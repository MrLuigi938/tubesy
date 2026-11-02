"""Download anyway: when yt-dlp does not know a page, Tubesy looks for the media itself."""
import pytest
from fastapi.testclient import TestClient

import conftest
from app.security import login_ip_limiter, login_user_limiter
from app.services.sniffer import find_media
from test_flow import ADMIN, login, wait_for


def test_find_media_in_page_text():
    page = "https://example.com/watch/42"
    text = """
    <html><head>
      <meta property="og:video" content="https://cdn.example.com/og.mp4">
      <script type="application/ld+json">{"@type": "VideoObject", "contentUrl": "https://cdn.example.com/ld.m3u8"}</script>
    </head><body>
      <video><source src="/media/clip.webm" type="video/webm"></video>
      <script>var cfg = {"hls": "https:\\/\\/stream.example.com\\/master.m3u8?token=a&amp;b=1", "poster": "https://example.com/p.jpg"};</script>
      <a href="https://example.com/download.mp3">mp3</a>
    </body></html>"""
    found = find_media(page, text)
    # Tags and metadata first, in page order; then adaptive streams before files.
    assert found[:3] == ["https://example.com/media/clip.webm", "https://cdn.example.com/og.mp4", "https://cdn.example.com/ld.m3u8"]
    assert "https://stream.example.com/master.m3u8?token=a&b=1" in found
    assert found.index("https://stream.example.com/master.m3u8?token=a&b=1") < found.index("https://example.com/download.mp3")
    assert not any(u.endswith(".jpg") for u in found)


@pytest.fixture
def pages(media_url):
    """Pages whose video only sits in a script (yt-dlp alone cannot find it)."""
    media = conftest._tmp / "media"
    clip = media_url.replace("/clip.mp4", "/clip.mp4").replace("/", "\\/")
    (media / "player.html").write_text(
        f'<html><head><title>Mein Film</title></head><body><div id="p"></div>'
        f'<script>window.player = {{"stream": "{clip}"}};</script></body></html>', encoding="utf-8")
    (media / "frame.html").write_text(
        '<html><head><title>Mit Rahmen</title></head><body><iframe src="player.html"></iframe></body></html>', encoding="utf-8")
    (media / "empty.html").write_text("<html><head><title>Leer</title></head><body>nichts</body></html>", encoding="utf-8")
    base = media_url.rsplit("/", 1)[0]
    return {name: f"{base}/{name}.html" for name in ("player", "frame", "empty")}


def queue(client, url, force):
    preset = next(p for p in client.get("/api/presets").json()["items"] if p["name"] == "Audio (MP3)")["id"]
    r = client.post("/api/downloads", json={"preset_id": preset, "items": [{"url": url}], "force": force})
    assert r.status_code == 200, r.text
    return r.json()[0]["id"]


def test_download_anyway_finds_the_video_on_the_page(client: TestClient, pages):
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, ADMIN)

    # Without forcing, yt-dlp's answer stands.
    d = wait_for(client, queue(client, pages["player"], force=False))
    assert d["status"] == "failed" and "Unsupported URL" in d["error"]

    # Forced: the stream in the script is found and downloaded, named after the page.
    d = wait_for(client, queue(client, pages["player"], force=True))
    assert d["status"] == "completed", d["error"]
    assert d["title"] == "Mein Film" and d["filename"].startswith("Mein Film")

    # Also one level deep in an iframe.
    d = wait_for(client, queue(client, pages["frame"], force=True))
    assert d["status"] == "completed", d["error"]

    # Nothing on the page: a clear message instead of yt-dlp's.
    d = wait_for(client, queue(client, pages["empty"], force=True))
    assert d["status"] == "failed" and d["error"].startswith("Auf der Seite wurde kein Video gefunden")
