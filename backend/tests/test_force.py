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
    # The address only exists at runtime – no media URL anywhere in the source.
    (media / "jsplayer.html").write_text(
        '<html><head><title>JS Film</title></head><body><video id="v" muted playsinline></video><script>'
        'const parts = ["cl", "ip", ".", "m", "p", "4"];'
        'setTimeout(() => { document.getElementById("v").src = parts.join(""); }, 300);'
        '</script></body></html>', encoding="utf-8")
    base = media_url.rsplit("/", 1)[0]
    return {name: f"{base}/{name}.html" for name in ("player", "frame", "empty", "jsplayer")}


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


def test_browser_finds_videos_that_only_javascript_loads(client: TestClient, pages, monkeypatch):
    from app.services import browser, sniffer

    if not browser.available():
        pytest.skip("no Chromium for the headless browser")
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, ADMIN)
    # The page source has nothing – only the running page knows the video.
    assert sniffer.find_media(pages["jsplayer"], (conftest._tmp / "media" / "jsplayer.html").read_text()) == []
    d = wait_for(client, queue(client, pages["jsplayer"], force=True), timeout=120)
    assert d["status"] == "completed", d["error"]
    assert d["title"] == "JS Film"


def test_browser_respects_the_local_address_guard(pages):
    import asyncio

    from app.services import browser

    if not browser.available():
        pytest.skip("no Chromium for the headless browser")

    # The page itself was checked before; what the player loads goes through the guard.
    async def media_blocked(url):
        return url.endswith(".mp4")

    cap = asyncio.run(browser.capture(pages["jsplayer"], media_blocked))
    assert cap.media == [] and cap.title == "JS Film"



def test_the_longest_video_wins_over_ads_and_decoys(monkeypatch):
    import asyncio

    from app.services import lengths

    durations = {
        "https://cdn.example.com/ad.mp4": 39.0,
        "https://cdn.example.com/film/master.m3u8": 1800.0,
        "https://cdn.example.com/film/index.m3u8": 1800.4,
        "https://test-videos.co.uk/vids/bigbuckbunny/mp4/Big_Buck_Bunny_10s.mp4": 10.0,
        "https://cdn.example.com/protected.m3u8": None,
    }

    async def measure(c):
        return durations[c.url]

    monkeypatch.setattr(lengths, "measure", measure)
    ranked = asyncio.run(lengths.rank([lengths.Candidate(u) for u in durations] + [lengths.Candidate("https://cdn.example.com/ad.mp4")]))
    assert [c.url for c in ranked] == [
        "https://cdn.example.com/film/master.m3u8",  # the master playlist keeps its place before its variant
        "https://cdn.example.com/film/index.m3u8",
        "https://cdn.example.com/protected.m3u8",  # unknown length: still worth a try
        "https://cdn.example.com/ad.mp4",  # far shorter than the film
        "https://test-videos.co.uk/vids/bigbuckbunny/mp4/Big_Buck_Bunny_10s.mp4",
    ]


def test_cookies_only_go_to_their_own_site():
    from app.services import lengths

    cookies = [{"name": "a", "value": "1", "domain": ".host.example"}, {"name": "b", "value": "2", "domain": "other.example"}]
    assert lengths.cookie_header(cookies, "https://cdn.host.example/x.m3u8") == "a=1"
    assert lengths.cookie_header(cookies, "https://evilhost.example/x.m3u8") == ""
