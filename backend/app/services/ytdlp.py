"""Everything that talks to yt-dlp.

yt-dlp is always run as a subprocess: a hanging extractor cannot block the
server, downloads can be cancelled by killing the process, and a yt-dlp
update takes effect without restarting Tubesy.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .. import config

SPONSORBLOCK_CATEGORIES = {
    "sponsor", "intro", "outro", "selfpromo", "preview", "filler", "interaction", "music_offtopic",
}
DEFAULT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"

PROGRESS_PREFIX = "TSPROG:"
POST_PREFIX = "TSPOST:"
FILE_PREFIX = "TSFILE:"


class PresetOptions(BaseModel):
    """Curated subset of yt-dlp options. Raw yt-dlp flags are deliberately not
    accepted, because options such as --exec would allow running commands."""

    mode: Literal["video", "audio"] = "video"
    quality: Literal["best", "2160", "1440", "1080", "720", "480", "360"] = "best"
    container: Literal["any", "mp4", "mkv", "webm"] = "mp4"
    audio_format: Literal["best", "mp3", "m4a", "opus", "flac", "wav"] = "mp3"
    audio_quality: Literal["best", "320", "256", "192", "128"] = "best"
    subtitles: bool = False
    auto_subtitles: bool = False
    sub_langs: str = "de,en"
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    embed_chapters: bool = True
    sponsorblock_remove: list[str] = Field(default_factory=list)
    output_template: str = DEFAULT_TEMPLATE

    @field_validator("sub_langs")
    @classmethod
    def _langs(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.*,\-]{1,100}", v or "x"):
            raise ValueError("Ungültige Untertitel-Sprachen")
        return v or "de,en"

    @field_validator("sponsorblock_remove")
    @classmethod
    def _sponsor(cls, v: list[str]) -> list[str]:
        unknown = set(v) - SPONSORBLOCK_CATEGORIES
        if unknown:
            raise ValueError(f"Unbekannte SponsorBlock-Kategorien: {', '.join(sorted(unknown))}")
        return sorted(set(v))

    @field_validator("output_template")
    @classmethod
    def _template(cls, v: str) -> str:
        v = v.strip() or DEFAULT_TEMPLATE
        if len(v) > 200 or v.startswith(("/", "\\", "~")) or ".." in v or "\n" in v:
            raise ValueError("Ungültige Dateinamen-Vorlage")
        if "%(ext)s" not in v:
            raise ValueError("Die Vorlage muss %(ext)s enthalten")
        return v


BUILTIN_PRESETS: list[tuple[str, dict]] = [
    ("Beste Qualität (MP4)", PresetOptions().model_dump()),
    ("1080p (MP4)", PresetOptions(quality="1080").model_dump()),
    ("720p (MP4)", PresetOptions(quality="720").model_dump()),
    ("Beste Qualität (MKV, Untertitel)", PresetOptions(container="mkv", subtitles=True).model_dump()),
    ("Audio (MP3)", PresetOptions(mode="audio", audio_format="mp3", audio_quality="320").model_dump()),
    ("Audio (Original)", PresetOptions(mode="audio", audio_format="best").model_dump()),
]


def build_args(opts: PresetOptions, home: Path, temp: Path, url: str, prefix: str = "") -> list[str]:
    args = [
        config.YTDLP_PYTHON, "-m", "yt_dlp",
        "--newline", "--progress", "--no-colors", "--no-simulate", "--no-playlist",
        "--no-mtime", "--windows-filenames", "--ignore-config",
        "--cache-dir", str(config.CACHE_DIR / "yt-dlp"),
        "-P", f"home:{home}", "-P", f"temp:{temp}",
        "--progress-template",
        f"download:{PROGRESS_PREFIX}%(progress.status)s|%(progress.downloaded_bytes)s|"
        "%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s|"
        "%(info.format_id)s",
        "--progress-template", f"postprocess:{POST_PREFIX}%(progress.status)s|%(progress.postprocessor)s",
        "--print", f"after_move:{FILE_PREFIX}%(filepath)s",
    ]

    if opts.mode == "audio":
        args += ["-f", "ba/b", "-x"]
        if opts.audio_format != "best":
            args += ["--audio-format", opts.audio_format]
        args += ["--audio-quality", "0" if opts.audio_quality == "best" else f"{opts.audio_quality}K"]
    else:
        args += ["-f", "bv*+ba/b"]
        sort = [] if opts.quality == "best" else [f"res:{opts.quality}"]
        if opts.container == "mp4":
            sort += ["vcodec:h264", "ext:mp4:m4a"]
        elif opts.container == "webm":
            sort += ["ext:webm:webm"]
        if sort:
            args += ["-S", ",".join(sort)]
        if opts.container != "any":
            args += ["--merge-output-format", opts.container, "--remux-video", opts.container]
        if opts.subtitles or opts.auto_subtitles:
            args += ["--sub-langs", opts.sub_langs, "--embed-subs"]
            args += ["--write-subs"] if opts.subtitles else []
            args += ["--write-auto-subs"] if opts.auto_subtitles else []
        if opts.embed_chapters:
            args += ["--embed-chapters"]
        if opts.sponsorblock_remove:
            args += ["--sponsorblock-remove", ",".join(opts.sponsorblock_remove)]

    if opts.embed_thumbnail:
        args += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
    if opts.embed_metadata:
        args += ["--embed-metadata"]

    # The prefix is literal text, so '%' has to be escaped for yt-dlp's template engine.
    # It goes in front of the file name, not in front of any sub-folders in the template.
    folder, _, name = opts.output_template.rpartition("/")
    template = f"{folder}/" if folder else ""
    args += ["-o", template + prefix.replace("%", "%%") + name]
    args += ["--", url]
    return args


def normalize_url(url: str) -> str:
    url = url.strip()
    # A bare YouTube channel URL lists its tabs; the "videos" tab is what people mean.
    m = re.fullmatch(r"(https?://(?:www\.|m\.)?youtube\.com/(?:@[^/?#]+|channel/[^/?#]+|c/[^/?#]+))/?", url)
    return f"{m.group(1)}/videos" if m else url


class ProbeError(Exception):
    pass


def _thumb(info: dict) -> str | None:
    if info.get("thumbnail"):
        return info["thumbnail"]
    thumbs = info.get("thumbnails") or []
    return thumbs[-1].get("url") if thumbs else None


async def probe(url: str, max_items: int, timeout: float = 120) -> dict:
    """Fetches metadata for a URL without downloading. Playlists are listed flat."""
    url = normalize_url(url)
    proc = await asyncio.create_subprocess_exec(
        config.YTDLP_PYTHON, "-m", "yt_dlp", "-J", "--flat-playlist", "--no-warnings", "--ignore-config",
        "--playlist-end", str(max_items), "--cache-dir", str(config.CACHE_DIR / "yt-dlp"), "--", url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        proc.kill()
        raise ProbeError("Zeitüberschreitung beim Abrufen der Informationen")
    if proc.returncode != 0:
        lines = [l for l in err.decode(errors="replace").splitlines() if l.strip()]
        msg = next((l for l in reversed(lines) if l.startswith("ERROR:")), lines[-1] if lines else "Unbekannter Fehler")
        raise ProbeError(msg.removeprefix("ERROR: "))
    info = json.loads(out)

    base = {
        "url": url,
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "thumbnail": _thumb(info),
        "extractor": info.get("extractor_key") or info.get("extractor"),
    }
    if info.get("_type") == "playlist":
        entries = []
        for i, entry in enumerate(info.get("entries") or [], start=1):
            if not entry:
                continue
            entry_url = entry.get("url") or entry.get("webpage_url")
            if not entry_url:
                continue
            if entry.get("_type") == "url" and entry.get("ie_key", "").endswith("Tab"):
                continue  # nested tab listing, not a video
            entries.append({
                "index": entry.get("playlist_index") or i,
                "url": entry_url,
                "video_id": entry.get("id"),
                "title": entry.get("title") or entry_url,
                "duration": entry.get("duration"),
                "thumbnail": _thumb(entry),
                "uploader": entry.get("uploader") or entry.get("channel") or base["uploader"],
            })
        return {**base, "type": "playlist", "count": len(entries), "entries": entries}

    return {
        **base,
        "type": "video",
        "url": info.get("webpage_url") or url,
        "video_id": info.get("id"),
        "duration": info.get("duration"),
    }


async def version() -> str:
    proc = await asyncio.create_subprocess_exec(
        config.YTDLP_PYTHON, "-m", "yt_dlp", "--version",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return out.decode().strip() or "unbekannt"


async def self_update() -> str:
    """Upgrades yt-dlp inside the running interpreter's environment."""
    proc = await asyncio.create_subprocess_exec(
        config.YTDLP_PYTHON, "-m", "pip", "install", "--no-cache-dir", "--disable-pip-version-check",
        "-q", "-U", "yt-dlp[default]",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(out.decode(errors="replace")[-500:])
    return await version()
