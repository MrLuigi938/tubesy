"""A headless Chromium that watches a page play its video.

The last resort behind "Download anyway": modern players build their stream
URL in JavaScript, so it never shows up in the page source. Here the page
really runs, the player is started (muted) and every response is watched –
HLS/DASH manifests and video/audio files are what we are after. yt-dlp then
downloads the best one with the browser's cookies, user agent and the page
as referer, as if the browser asked.

Chromium comes with the Docker image (TUBESY_CHROMIUM); without it the
feature is simply off and the page-source search remains.
"""
import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger("tubesy.browser")

WAIT = 25  # seconds to wait for the player to load media
GRACE = 2  # after the first stream showed up, for its siblings
MIN_FILE = 300 * 1024  # smaller files are usually ads, previews or sounds
_MANIFEST_EXT = (".m3u8", ".mpd")
_FILE_EXT = (".mp4", ".m4v", ".webm", ".mov", ".mkv", ".mp3", ".m4a", ".ogg", ".opus", ".flac", ".wav")
_SEGMENT_EXT = (".ts", ".m4s", ".aac", ".vtt", ".key")
_MANIFEST_TYPES = ("mpegurl", "dash+xml")
_PLAY_BUTTONS = (
    ".vjs-big-play-button", ".jw-icon-display", ".plyr__control--overlaid", ".ytp-large-play-button",
    "button[aria-label*='play' i]", "button[title*='play' i]", "[class*='play-button' i]", "[class*='playbutton' i]",
)
_PLAY_JS = """() => {
    for (const v of document.querySelectorAll('video, audio')) {
        v.muted = true;
        const p = v.play();
        if (p && p.catch) p.catch(() => {});
    }
}"""

_lock = asyncio.Semaphore(1)  # one page at a time: Chromium is memory-hungry


@dataclass
class Media:
    url: str
    kind: str  # "stream" (HLS/DASH manifest) or "file"
    size: int | None = None


@dataclass
class Capture:
    media: list[Media] = field(default_factory=list)
    title: str | None = None
    user_agent: str | None = None
    cookies: list[dict] = field(default_factory=list)


def executable() -> str | None:
    """The Chromium to use: TUBESY_CHROMIUM, a system browser, or Playwright's own."""
    if os.environ.get("TUBESY_CHROMIUM"):
        return os.environ["TUBESY_CHROMIUM"]
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    return None


def available() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return bool(executable() or os.environ.get("PLAYWRIGHT_BROWSERS_PATH"))


def _size(headers: dict) -> int | None:
    total = headers.get("content-range", "").rpartition("/")[2]
    for value in (total, headers.get("content-length", "")):
        if value.isdigit():
            return int(value)
    return None


def _classify(url: str, content_type: str) -> str | None:
    path = urlsplit(url).path.lower()
    if url.startswith(("blob:", "data:")) or path.endswith(_SEGMENT_EXT):
        return None
    if path.endswith(_MANIFEST_EXT) or any(t in content_type for t in _MANIFEST_TYPES):
        return "stream"
    if path.endswith(_FILE_EXT) or content_type.startswith(("video/", "audio/")):
        return "file"
    return None


def best(found: dict[str, Media]) -> list[Media]:
    """Streams first in the order they appeared (the master playlist comes first),
    then real files, biggest first."""
    streams = [m for m in found.values() if m.kind == "stream"]
    files = sorted((m for m in found.values() if m.kind == "file"), key=lambda m: -(m.size or 0))
    # Small files are usually ads or previews – but only drop them next to bigger ones.
    if any((m.size or 0) >= MIN_FILE for m in files):
        files = [m for m in files if (m.size or MIN_FILE) >= MIN_FILE]
    return streams + files


async def _start_playback(page) -> None:
    for frame in page.frames:
        try:
            await frame.evaluate(_PLAY_JS)
        except Exception:
            continue
        for selector in _PLAY_BUTTONS:
            try:
                button = frame.locator(selector).first
                if await button.is_visible(timeout=200):
                    await button.click(timeout=800)
                    break
            except Exception:
                continue


async def capture(url: str, is_blocked=None) -> Capture:
    """Opens the page, starts its player and returns the media it loaded.

    is_blocked(url) -> bool (async) can veto requests, e.g. to local addresses."""
    from playwright.async_api import async_playwright

    found: dict[str, Media] = {}
    result = Capture()
    async with _lock, async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=executable(),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required", "--mute-audio"],
        )
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 720}, locale="de-DE")
            if is_blocked is not None:
                async def guard(route):
                    if await is_blocked(route.request.url):
                        await route.abort()
                    else:
                        await route.continue_()

                await context.route("**/*", guard)

            def on_response(response):
                kind = _classify(response.url, (response.headers.get("content-type") or "").lower())
                if kind and response.url not in found:
                    found[response.url] = Media(response.url, kind, _size(response.headers))

            context.on("response", on_response)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            deadline, seen_at = time.monotonic() + WAIT, None
            while time.monotonic() < deadline:
                await _start_playback(page)
                await asyncio.sleep(1.5)
                if any(m.kind == "stream" for m in found.values()) or best(found):
                    seen_at = seen_at or time.monotonic()
                    if time.monotonic() - seen_at >= GRACE:
                        break
            result.title = (await page.title()) or None
            result.user_agent = await page.evaluate("navigator.userAgent")
            result.cookies = await context.cookies()
        finally:
            await browser.close()
    result.media = best(found)
    log.info("Browser: %d Medien auf %s gefunden", len(result.media), url)
    return result


def write_cookies(cookies: list[dict], path: Path) -> Path:
    """The browser's cookies as a Netscape cookie file for yt-dlp."""
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        expires = int(c.get("expires") or 0)
        lines.append("\t".join([
            domain, "TRUE" if domain.startswith(".") else "FALSE", c.get("path", "/"),
            "TRUE" if c.get("secure") else "FALSE", str(max(expires, 0)), c.get("name", ""), c.get("value", ""),
        ]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
