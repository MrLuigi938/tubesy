"""Download queue: schedules queued rows onto yt-dlp subprocesses."""
import asyncio
import json
import logging
import os
import re
import shutil
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config
from ..database import SessionLocal
from ..models import Download, User
from . import notify, sniffer
from . import settings as app_settings
from .events import hub
from .netcheck import is_local
from .ytdlp import FILE_PREFIX, META_PREFIX, POST_PREFIX, PROGRESS_PREFIX, PresetOptions, build_args

log = logging.getLogger("tubesy.downloads")

ACTIVE = ("downloading", "processing")
FINISHED = ("completed", "failed", "canceled")
_EMIT_INTERVAL = 0.5

_POSTPROCESSOR_LABELS = {
    "Merger": "Zusammenführen",
    "FFmpegMerger": "Zusammenführen",
    "ExtractAudio": "Audio extrahieren",
    "FFmpegExtractAudio": "Audio extrahieren",
    "EmbedThumbnail": "Thumbnail einbetten",
    "ThumbnailsConvertor": "Thumbnail umwandeln",
    "FFmpegThumbnailsConvertor": "Thumbnail umwandeln",
    "FFmpegMetadata": "Metadaten",
    "Metadata": "Metadaten",
    "EmbedSubtitle": "Untertitel einbetten",
    "SponsorBlock": "SponsorBlock",
    "ModifyChapters": "Kapitel anpassen",
    "VideoRemuxer": "Remuxen",
    "MoveFiles": "Verschieben",
}


def user_root(user: User) -> Path:
    return config.DOWNLOAD_DIR / user.username


def safe_component(name: str, fallback: str = "Playlist") -> str:
    """Turns a playlist title into a folder name that is valid on SMB/NFS shares."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip(" .")
    return (name[:120].rstrip(" .") or fallback)


def permission_hint() -> str:
    return (
        f"Keine Schreibrechte auf den Download-Ordner (Container läuft als UID {os.getuid()}, "
        f"GID {os.getgid()}). Auf der NAS den Ordner diesem Benutzer geben, z. B. "
        f"'chown -R {os.getuid()}:{os.getgid()} <ordner>', oder PUID/PGID anpassen."
    )


def download_dir_writable() -> bool:
    return os.access(config.DOWNLOAD_DIR, os.W_OK | os.X_OK)


def used_bytes(db: Session, user_id: int) -> int:
    total = (
        db.query(func.coalesce(func.sum(Download.file_size), 0))
        .filter(Download.user_id == user_id, Download.status == "completed")
        .scalar()
    )
    return int(total or 0)


QUOTA_EXCEEDED = "Speicherkontingent würde überschritten"
NOTHING_FOUND = "Auf der Seite wurde kein Video gefunden – vermutlich lädt sie es erst per JavaScript"
ADULT_AGE = 18

# What is withheld for hidden videos until they are revealed.
_HIDDEN_FIELDS = ("url", "video_id", "title", "uploader", "thumbnail", "playlist_title", "filename")


def serialize(d: Download, live: dict | None = None, reveal: bool = False) -> dict:
    """The download as the API returns it. For a hidden video, title, thumbnail and
    everything else that tells what it is stay out unless reveal is set."""
    data = {
        "id": d.id,
        "user_id": d.user_id,
        "username": d.user.username if d.user else None,
        "url": d.url,
        "video_id": d.video_id,
        "title": d.title,
        "uploader": d.uploader,
        "thumbnail": d.thumbnail,
        "duration": d.duration,
        "preset_name": d.preset_name,
        "mode": (d.options or {}).get("mode", "video"),
        "playlist_title": d.playlist_title,
        "playlist_index": d.playlist_index,
        "subscription_id": d.subscription_id,
        "status": d.status,
        "progress": d.progress,
        "error": d.error,
        "filename": Path(d.file_path).name if d.file_path else None,
        "file_size": d.file_size,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "started_at": d.started_at.isoformat() if d.started_at else None,
        "finished_at": d.finished_at.isoformat() if d.finished_at else None,
        "speed": None,
        "eta": None,
        "downloaded_bytes": None,
        "total_bytes": None,
        "stage": None,
        "hidden": d.hidden,
        "age_limit": d.age_limit,
    }
    if live:
        data.update(live)
    if d.hidden and not reveal:
        data.update(dict.fromkeys(_HIDDEN_FIELDS))
    return data


def resolve_file(d: Download) -> Path | None:
    """The finished file of a download, if it still exists inside the download folder."""
    if not d.file_path:
        return None
    path = (config.DOWNLOAD_DIR / d.file_path).resolve()
    if not path.is_relative_to(config.DOWNLOAD_DIR) or not path.is_file():
        return None
    return path


def delete_file(d: Download) -> None:
    """Deletes the file and an emptied playlist folder."""
    path = resolve_file(d)
    if path is None:
        return
    path.unlink(missing_ok=True)
    # Remove an emptied playlist folder, but never the user's root folder.
    parent = path.parent
    root = (config.DOWNLOAD_DIR / d.user.username).resolve()
    if parent != root and parent.is_relative_to(root) and not any(parent.iterdir()):
        parent.rmdir()


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class DownloadManager:
    def __init__(self) -> None:
        self._procs: dict[int, asyncio.subprocess.Process | None] = {}
        self._tasks: set[asyncio.Task] = set()
        self._cancel_requested: set[int] = set()
        self._over_quota: set[int] = set()
        self._live: dict[int, dict] = {}
        self._wake = asyncio.Event()
        self._loop_task: asyncio.Task | None = None

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        with SessionLocal() as db:
            # Anything that was running when the container stopped starts over.
            db.query(Download).filter(Download.status.in_(ACTIVE)).update(
                {"status": "queued", "progress": 0.0}, synchronize_session=False
            )
            db.commit()
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self._loop_task = asyncio.create_task(self._loop())
        self.wake()

    async def stop(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
        for proc in self._procs.values():
            if proc and proc.returncode is None:
                proc.kill()
        for task in list(self._tasks):
            task.cancel()

    def _background(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def wake(self) -> None:
        self._wake.set()

    def live(self, download_id: int) -> dict | None:
        return self._live.get(download_id)

    # -- control -------------------------------------------------------------

    def cancel(self, download_id: int) -> bool:
        """Stops a running download. Returns False if it was not running."""
        if download_id not in self._procs:
            return False
        self._cancel_requested.add(download_id)
        proc = self._procs.get(download_id)
        if proc and proc.returncode is None:
            proc.kill()
        return True

    def cancel_user(self, user_id: int, db: Session) -> None:
        ids = [i for (i,) in db.query(Download.id).filter(Download.user_id == user_id, Download.id.in_(list(self._procs)))]
        for download_id in ids:
            self.cancel(download_id)

    # -- scheduling ----------------------------------------------------------

    async def _loop(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            try:
                self._fill_slots()
            except Exception:
                log.exception("Scheduler error")

    def _fill_slots(self) -> None:
        with SessionLocal() as db:
            cfg = app_settings.get_all(db)
            max_total = max(1, int(cfg["max_concurrent_downloads"]))
            max_user = max(1, int(cfg["max_concurrent_per_user"]))
            free = max_total - len(self._procs)
            if free <= 0:
                return

            per_user: dict[int, int] = {}
            for (uid,) in db.query(Download.user_id).filter(Download.id.in_(list(self._procs))):
                per_user[uid] = per_user.get(uid, 0) + 1

            queued = (
                db.query(Download.id, Download.user_id)
                .filter(Download.status == "queued")
                .order_by(Download.created_at, Download.id)
                .all()
            )
            for download_id, uid in queued:
                if free <= 0:
                    break
                if per_user.get(uid, 0) >= max_user:
                    continue
                per_user[uid] = per_user.get(uid, 0) + 1
                free -= 1
                self._procs[download_id] = None  # reserve the slot before the task runs
                task = asyncio.create_task(self._run(download_id))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    # -- execution -----------------------------------------------------------

    async def _emit(self, d: Download) -> None:
        await hub.publish("download", serialize(d, self._live.get(d.id)), d.user_id)

    async def _run(self, download_id: int) -> None:
        temp = config.TEMP_DIR / str(download_id)
        db = SessionLocal()
        try:
            d = db.get(Download, download_id)
            if d is None or d.status != "queued":
                return
            user = d.user

            quota = user.quota_bytes
            quota_left = None if quota is None else quota - used_bytes(db, user.id)
            if quota_left is not None and quota_left <= 0:
                d.status, d.error = "failed", "Speicherkontingent erreicht"
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
                await self._emit(d)
                return

            home = user_root(user)
            if d.subfolder:
                home = home / d.subfolder
            try:
                home.mkdir(parents=True, exist_ok=True)
                temp.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                d.status, d.error = "failed", permission_hint()
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
                await self._emit(d)
                return

            prefix = f"{d.playlist_index:03d} - " if d.subfolder and d.playlist_index else ""
            opts = PresetOptions(**d.options)
            args = build_args(opts, home, temp, d.url, prefix, impersonate=d.forced)

            d.status, d.progress, d.error = "downloading", 0.0, None
            d.started_at = datetime.now(timezone.utc)
            db.commit()
            self._live[download_id] = {"stage": "Startet"}
            await self._emit(d)

            output_file, tail, code = await self._attempt(d, args, temp, quota_left)
            stopped = download_id in self._cancel_requested or download_id in self._over_quota
            if d.forced and not stopped and (code != 0 or not output_file):
                output_file, tail, code = await self._force(d, opts, home, temp, prefix, quota_left)

            d.finished_at = datetime.now(timezone.utc)
            if download_id in self._over_quota:
                d.status, d.error = "failed", QUOTA_EXCEEDED
            elif download_id in self._cancel_requested:
                d.status, d.error = "canceled", None
            elif code == 0 and output_file and output_file.is_file():
                d.status, d.progress = "completed", 100.0
                d.file_path = str(output_file.relative_to(config.DOWNLOAD_DIR))
                d.file_size = output_file.stat().st_size
            else:
                d.status = "failed"
                errors = [l.removeprefix("ERROR: ") for l in tail if l.startswith("ERROR:")]
                d.error = (errors[-1] if errors else (tail[-1] if tail else f"yt-dlp beendet mit Code {code}"))[:2000]
            db.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Download %s crashed", download_id)
            db.rollback()
            d = db.get(Download, download_id)
            if d is not None:
                d.status, d.error = "failed", f"Interner Fehler: {exc}"
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            self._procs.pop(download_id, None)
            self._cancel_requested.discard(download_id)
            self._over_quota.discard(download_id)
            self._live.pop(download_id, None)
            shutil.rmtree(temp, ignore_errors=True)
            try:
                d = db.get(Download, download_id)
                if d is not None:
                    await self._emit(d)
                    if d.status in ("completed", "failed"):
                        self._background(notify.download_finished(download_id))
            finally:
                db.close()
            self.wake()

    async def _attempt(
        self, d: Download, args: list[str], temp: Path, quota_left: int | None
    ) -> tuple[Path | None, deque[str], int | None]:
        """Runs yt-dlp once; returns the file, the last output lines and the exit code."""
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=temp, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            limit=1024 * 1024,
        )
        self._procs[d.id] = proc
        if d.id in self._cancel_requested:
            proc.kill()
        output_file, tail = await self._consume(d, proc, quota_left)
        await proc.wait()
        return output_file, tail, proc.returncode

    async def _force(
        self, d: Download, opts: PresetOptions, home: Path, temp: Path, prefix: str, quota_left: int | None
    ) -> tuple[Path | None, deque[str], int | None]:
        """yt-dlp could not handle the page: look for media on it ourselves and
        download what we find directly (the page goes along as referer)."""
        live = self._live[d.id]
        live.update({"stage": "Suche Video auf der Seite", "speed": None, "eta": None})
        await self._emit(d)
        try:
            found = await asyncio.to_thread(sniffer.sniff, d.url)
        except Exception as exc:
            return None, deque([f"ERROR: {NOTHING_FOUND} ({exc})"]), 1
        db = SessionLocal.object_session(d)
        if found.title and (not d.title or d.title == d.url):
            d.title = found.title
            db.commit()
        allow_local = d.user.is_admin or app_settings.get(db, "allow_local_urls")
        tail: deque[str] = deque([f"ERROR: {NOTHING_FOUND}"])
        for media in found.candidates:
            if not allow_local and await is_local(media):
                continue
            log.info("Download %s: Video auf der Seite gefunden: %s", d.id, media)
            live.update({"stage": "Download"})
            args = build_args(opts, home, temp, media, prefix, referer=d.url, title=found.title)
            output_file, tail, code = await self._attempt(d, args, temp, quota_left)
            if code == 0 and output_file:
                return output_file, tail, code
            if d.id in self._cancel_requested or d.id in self._over_quota:
                break
        return None, tail, 1

    def _stop_over_quota(self, d: Download, proc: asyncio.subprocess.Process) -> None:
        self._over_quota.add(d.id)
        if proc.returncode is None:
            proc.kill()

    def _apply_meta(self, d: Download, meta: dict) -> int | None:
        """Fills in what the check did not know (e.g. after "download anyway"),
        hides 18+ videos if the user wants that, and returns the expected size."""
        if not d.title or d.title == d.url:
            d.title = meta.get("title") or d.title
        d.uploader = d.uploader or meta.get("uploader") or meta.get("channel")
        d.thumbnail = d.thumbnail or meta.get("thumbnail")
        d.duration = d.duration or meta.get("duration")
        d.video_id = d.video_id or meta.get("id")
        age = meta.get("age_limit")
        if isinstance(age, int):
            d.age_limit = age
            if age >= ADULT_AGE and d.user.auto_hide_adult:
                d.hidden = True
        size = meta.get("filesize") or meta.get("filesize_approx")
        return int(size) if isinstance(size, (int, float)) else None

    async def _consume(
        self, d: Download, proc: asyncio.subprocess.Process, quota_left: int | None = None
    ) -> tuple[Path | None, deque[str]]:
        tail: deque[str] = deque(maxlen=40)
        output_file: Path | None = None
        streams: list[str] = []
        finished_bytes = 0.0  # earlier streams (video and audio are loaded one after the other)
        last_emit = 0.0
        live = self._live[d.id]
        db = SessionLocal.object_session(d)

        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            if not line:
                continue

            if line.startswith(PROGRESS_PREFIX):
                status, done, total, estimate, speed, eta, fmt = (line[len(PROGRESS_PREFIX):].split("|") + [""] * 7)[:7]
                if fmt not in streams:
                    streams.append(fmt)
                done_n, total_n = _num(done), _num(total) or _num(estimate)
                live.update({
                    "downloaded_bytes": done_n,
                    "total_bytes": total_n,
                    "speed": _num(speed),
                    "eta": _num(eta),
                    "stage": f"Download Stream {len(streams)}" if len(streams) > 1 else "Download",
                })
                if total_n and done_n is not None:
                    d.progress = round(min(100.0, done_n / total_n * 100), 1)
                if status == "finished":
                    d.progress = 100.0
                    finished_bytes += done_n or 0
                live["progress"] = d.progress
                if quota_left is not None and finished_bytes + (0 if status == "finished" else done_n or 0) > quota_left:
                    self._stop_over_quota(d, proc)
                # Some postprocessors (thumbnail conversion) run before the download starts.
                if d.status == "processing":
                    d.status = "downloading"
                    db.commit()
            elif line.startswith(POST_PREFIX):
                status, name = (line[len(POST_PREFIX):].split("|") + [""])[:2]
                if status == "started":
                    if d.status != "processing":
                        d.status = "processing"
                        db.commit()
                    live.update({"stage": _POSTPROCESSOR_LABELS.get(name, name), "speed": None, "eta": None})
            elif line.startswith(META_PREFIX):
                try:
                    meta = json.loads(line[len(META_PREFIX):])
                except ValueError:
                    continue
                expected = self._apply_meta(d, meta)
                db.commit()
                if quota_left is not None and expected and expected > quota_left:
                    self._stop_over_quota(d, proc)
                await self._emit(d)
                continue
            elif line.startswith(FILE_PREFIX):
                candidate = Path(line[len(FILE_PREFIX):]).resolve()
                if candidate.is_relative_to(config.DOWNLOAD_DIR):
                    output_file = candidate
                continue
            else:
                tail.append(line)
                continue

            now = time.monotonic()
            if now - last_emit >= _EMIT_INTERVAL:
                last_emit = now
                await self._emit(d)
        return output_file, tail


manager = DownloadManager()
