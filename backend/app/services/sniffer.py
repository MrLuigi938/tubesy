"""Finds video and audio sources on a web page by itself – the fallback behind
"Download anyway" when yt-dlp does not know the site.

It looks where players usually keep their media: <video>/<source>/<audio>
tags, og:video / twitter:player:stream, JSON-LD contentUrl, and any
.m3u8/.mpd/.mp4/… address in the page text or its scripts – also one level
deep in embedded iframes. The page is fetched like a browser does (curl_cffi
impersonation when installed). Videos a page only loads later via
JavaScript cannot be found this way.
"""
import html
import json
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

log = logging.getLogger("tubesy.sniffer")

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 20
MAX_IFRAMES = 3
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

_EXT = r"m3u8|mpd|mp4|m4v|webm|mov|mkv|mp3|m4a|aac|ogg|oga|opus|flac|wav"
_MEDIA_URL = re.compile(rf"""https?://[^\s"'<>()\\]+?\.(?:{_EXT})(?:\?[^\s"'<>\\]*)?(?=["'\s<>\\)]|$)""", re.I)
_TAG_SRC = re.compile(r"""<(?:video|source|audio)\b[^>]*?\ssrc\s*=\s*["']([^"']+)["']""", re.I)
_META = re.compile(
    r"""<meta\b[^>]*?(?:property|name)\s*=\s*["'](?:og:video(?::secure_url|:url)?|twitter:player:stream)["'][^>]*?content\s*=\s*["']([^"']+)["']""",
    re.I,
)
_META_REV = re.compile(
    r"""<meta\b[^>]*?content\s*=\s*["']([^"']+)["'][^>]*?(?:property|name)\s*=\s*["'](?:og:video(?::secure_url|:url)?|twitter:player:stream)["']""",
    re.I,
)
_IFRAME = re.compile(r"""<iframe\b[^>]*?\ssrc\s*=\s*["']([^"']+)["']""", re.I)
_TITLE = re.compile(r"""<meta\b[^>]*?property\s*=\s*["']og:title["'][^>]*?content\s*=\s*["']([^"']+)["']|<title[^>]*>([^<]+)</title>""", re.I)
_LD_JSON = re.compile(r"""<script[^>]*application/ld\+json[^>]*>(.*?)</script>""", re.I | re.S)


@dataclass
class Found:
    candidates: list[str] = field(default_factory=list)
    title: str | None = None


def fetch(url: str, referer: str | None = None) -> tuple[str, str]:
    """Returns (final URL, page text). Uses browser impersonation when available."""
    headers = {"User-Agent": UA, "Accept-Language": "de,en;q=0.8"}
    if referer:
        headers["Referer"] = referer
    try:
        from curl_cffi import requests as cffi

        r = cffi.get(url, impersonate="chrome", headers={k: v for k, v in headers.items() if k != "User-Agent"},
                     timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return str(r.url), r.content[:MAX_BYTES].decode(r.encoding or "utf-8", errors="replace")
    except ImportError:
        pass
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = resp.read(MAX_BYTES)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.geturl(), data.decode(charset, errors="replace")


def _ld_urls(text: str) -> list[str]:
    out = []
    for block in _LD_JSON.findall(text):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for key in ("contentUrl", "embedUrl"):
                    if isinstance(item.get(key), str):
                        out.append(item[key])
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    return out


def _rank(url: str) -> int:
    """Adaptive streams first (they carry every quality), then plain video, then audio."""
    path = urlsplit(url).path.lower()
    if path.endswith((".m3u8", ".mpd")):
        return 0
    if path.endswith((".mp4", ".m4v", ".webm", ".mov", ".mkv")):
        return 1
    return 2


def find_media(page_url: str, text: str) -> list[str]:
    """Media addresses in one page, best first."""
    clean = html.unescape(text).replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    explicit = [*_TAG_SRC.findall(clean), *_META.findall(clean), *_META_REV.findall(clean), *_ld_urls(text)]
    found: list[str] = []
    for raw in explicit + _MEDIA_URL.findall(clean):
        url = urljoin(page_url, raw.strip())
        if url.startswith(("http://", "https://")) and not url.startswith("blob:") and url not in found:
            found.append(url)
    # Tags and metadata name the main media; keep their order, then the rest by type.
    head = [u for u in found if u in {urljoin(page_url, x.strip()) for x in explicit}]
    rest = sorted((u for u in found if u not in head), key=_rank)
    return head + rest


def sniff(url: str) -> Found:
    """Looks for media on the page and, if needed, in its iframes."""
    final, text = fetch(url)
    match = _TITLE.search(text)
    title = html.unescape((match.group(1) or match.group(2)).strip()) if match else None
    candidates = find_media(final, text)
    if not candidates:
        for src in _IFRAME.findall(text)[:MAX_IFRAMES]:
            frame = urljoin(final, html.unescape(src))
            if not frame.startswith(("http://", "https://")):
                continue
            try:
                frame_final, frame_text = fetch(frame, referer=final)
            except Exception as exc:
                log.info("iframe %s: %s", frame, exc)
                continue
            candidates += [c for c in find_media(frame_final, frame_text) if c not in candidates]
    return Found(candidates=candidates[:5], title=title)
