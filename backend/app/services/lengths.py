"""Puts the media found by "Download anyway" in a sensible order.

Hoster pages are full of decoys: ad clips before the film, short previews,
test videos planted in the page source. Downloading the first hit is how a
30-minute episode turns into a 39-second clip. So every candidate is
measured with ffprobe first (with the same referer, user agent and cookies
the download will use) and the longest wins; clips far shorter than it are
dropped.
"""
import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from urllib.parse import urlsplit

log = logging.getLogger("tubesy.lengths")

TIMEOUT = 25
SHORT = 0.5  # shorter than half the longest one: an ad or a preview
# Sample videos that hosters put into their page source as bait.
_DECOY_HOSTS = ("test-videos.co.uk", "sample-videos.com", "samplelib.com", "file-examples.com")
_DECOY_PATHS = ("/gtv-videos-bucket/sample/", "big_buck_bunny", "bigbuckbunny")


@dataclass
class Candidate:
    url: str
    referer: str | None = None
    user_agent: str | None = None
    cookies: list[dict] = field(default_factory=list)
    duration: float | None = None


def is_decoy(url: str) -> bool:
    parts = urlsplit(url)
    host, path = parts.hostname or "", parts.path.lower()
    return host.endswith(_DECOY_HOSTS) or any(p in path for p in _DECOY_PATHS)


def cookie_header(cookies: list[dict], url: str) -> str:
    host = urlsplit(url).hostname or ""
    pairs = [
        f"{c['name']}={c['value']}" for c in cookies
        if host == c.get("domain", "").lstrip(".") or host.endswith("." + c.get("domain", "").lstrip("."))
    ]
    return "; ".join(pairs)


async def measure(c: Candidate) -> float | None:
    """The length in seconds, or None when ffprobe cannot tell."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    headers = ""
    if c.referer:
        headers += f"Referer: {c.referer}\r\n"
    cookie = cookie_header(c.cookies, c.url)
    if cookie:
        headers += f"Cookie: {cookie}\r\n"
    args = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1"]
    if c.user_agent:
        args += ["-user_agent", c.user_agent]
    if headers:
        args += ["-headers", headers]
    proc = await asyncio.create_subprocess_exec(
        *args, c.url, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        return None
    try:
        return float(out.decode().strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


async def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Longest first, then those that could not be measured; decoys and clips far
    shorter than the longest one only when nothing else is left."""
    unique: dict[str, Candidate] = {}
    for c in candidates:
        unique.setdefault(c.url, c)
    items = list(unique.values())
    durations = await asyncio.gather(*(measure(c) for c in items), return_exceptions=True)
    for c, d in zip(items, durations):
        c.duration = d if isinstance(d, float) and d > 0 else None
        log.info("Kandidat %s: %s s", c.url, c.duration)
    longest = max((c.duration for c in items if c.duration and not is_decoy(c.url)), default=0)

    def order(c: Candidate) -> tuple[int, float]:
        if is_decoy(c.url):
            return 3, 0
        if c.duration is None:
            return 1, 0
        if c.duration < longest * SHORT:
            return 2, -c.duration
        return 0, -round(c.duration)

    return sorted(items, key=order)
