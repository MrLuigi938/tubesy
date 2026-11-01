"""Version 1.2: subscriptions, notifications, clean-up rules."""
import asyncio
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app.security import login_ip_limiter, login_user_limiter
from test_flow import ADMIN, login, wait_for

USER = {"username": "abonnentin", "password": "abo-passwort-12"}


@pytest.fixture(autouse=True)
def _no_rate_limit():
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()


@pytest.fixture(scope="module", autouse=True)
def _user(client):
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, ADMIN)
    client.post("/api/admin/users", json=USER)
    client.put("/api/admin/settings", json={"allow_local_urls": True})


@pytest.fixture
def channel(monkeypatch, media_url):
    """A fake channel listing instead of asking a real site."""
    entries = [{"index": i, "url": f"{media_url}?v{i}", "video_id": f"v{i}", "title": f"Folge {i}",
                "duration": 3, "thumbnail": None, "uploader": "Kanal"} for i in (3, 2, 1)]  # newest first

    async def probe(url, max_items, timeout=120):
        if url.endswith("/single"):
            return {"type": "video", "url": url, "title": "x", "uploader": None, "thumbnail": None, "extractor": "Generic"}
        return {"type": "playlist", "url": url, "title": "Testkanal", "uploader": "Kanal", "thumbnail": None,
                "extractor": "Youtube", "count": len(entries), "entries": list(entries)}

    from app.services import ytdlp
    monkeypatch.setattr(ytdlp, "probe", probe)
    return entries


def test_subscriptions(client: TestClient, channel, media_url):
    login(client, USER)
    url = "https://www.youtube.com/@testkanal/videos"
    r = client.post("/api/subscriptions", json={"url": url, "backfill": 1, "interval_hours": 6})
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["title"] == "Testkanal" and sub["queued"] == 1
    # The newest video is downloaded, into the subscription's folder.
    first = next(d for d in client.get("/api/downloads?view=all").json()["items"] if d["subscription_id"] == sub["id"])
    assert first["title"] == "Folge 3" and first["playlist_title"] == "Testkanal"
    wait_for(client, first["id"])

    assert client.post("/api/subscriptions", json={"url": url}).status_code == 409
    single = client.post("/api/subscriptions", json={"url": "https://example.com/single"})
    assert single.status_code == 422

    # Nothing new: nothing queued. A new video: exactly that one.
    assert client.post(f"/api/subscriptions/{sub['id']}/check").json()["queued"] == 0
    channel.insert(0, {"index": 4, "url": f"{media_url}?v4", "video_id": "v4", "title": "Folge 4",
                       "duration": 3, "thumbnail": None, "uploader": "Kanal"})
    checked = client.post(f"/api/subscriptions/{sub['id']}/check").json()
    assert checked["queued"] == 1 and checked["downloads"] == 2

    # A deleted download is not fetched again.
    for d in client.get("/api/downloads?view=all").json()["items"]:
        if d["subscription_id"] == sub["id"]:
            wait_for(client, d["id"])
            client.delete(f"/api/downloads/{d['id']}")
    assert client.post(f"/api/subscriptions/{sub['id']}/check").json()["queued"] == 0

    r = client.patch(f"/api/subscriptions/{sub['id']}", json={"enabled": False, "interval_hours": 24, "hidden": True})
    assert r.json()["enabled"] is False and r.json()["interval_hours"] == 24 and r.json()["hidden"] is True
    assert client.patch(f"/api/subscriptions/{sub['id']}", json={"interval_hours": 5}).status_code == 422
    assert client.delete(f"/api/subscriptions/{sub['id']}").status_code == 200
    assert client.get("/api/subscriptions").json() == []


def test_subscription_is_due():
    from app.models import Subscription
    from app.services.subscriptions import is_due

    now = datetime.now(timezone.utc)
    assert is_due(Subscription(enabled=True, interval_hours=6, last_checked_at=None), now)
    assert not is_due(Subscription(enabled=True, interval_hours=6, last_checked_at=now - timedelta(hours=5)), now)
    assert is_due(Subscription(enabled=True, interval_hours=6, last_checked_at=now - timedelta(hours=6)), now)
    assert not is_due(Subscription(enabled=False, interval_hours=6, last_checked_at=None), now)


@pytest.fixture
def ntfy():
    """A local stand-in for an ntfy server that records the messages."""
    received: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"])).decode()
            received.append((self.headers.get("Authorization", ""), body))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/tubesy", received
    server.shutdown()


def test_notifications(client: TestClient, ntfy, media_url):
    url, received = ntfy
    login(client, USER)
    r = client.put("/api/account/notifications", json={"ntfy_url": url, "ntfy_token": "geheim", "on_done": True, "on_failed": True})
    assert r.status_code == 200
    settings = client.get("/api/account/notifications").json()
    assert settings["ntfy_token_set"] is True and "ntfy_token" not in settings

    assert client.post("/api/account/notifications/test").status_code == 200
    assert received[-1][0] == "Bearer geheim" and "Hallo" in received[-1][1]

    preset = next(p for p in client.get("/api/presets").json()["items"] if p["name"] == "Audio (MP3)")["id"]
    d = client.post("/api/downloads", json={"preset_id": preset, "items": [{"url": media_url + "?notify"}]}).json()[0]
    wait_for(client, d["id"])
    hidden = client.post("/api/downloads", json={"preset_id": preset, "hidden": True, "items": [{"url": media_url + "?secret"}]}).json()[0]
    wait_for(client, hidden["id"])
    for _ in range(50):  # sent in the background
        if len(received) >= 3:
            break
        asyncio.run(asyncio.sleep(0.1))
    texts = [body for _, body in received[1:]]
    assert any(t.startswith("Fertig: clip") for t in texts)
    assert any("ausgeblendetes Video" in t for t in texts) and not any("secret" in t for t in texts)

    # Keep the token (None), remove the URL: nothing is sent any more.
    client.put("/api/account/notifications", json={"ntfy_url": ""})
    assert client.get("/api/account/notifications").json()["ntfy_token_set"] is True
    assert client.post("/api/account/notifications/test").status_code == 400


def test_clean_up_rules(client: TestClient, monkeypatch, downloads_dir):
    from app.database import SessionLocal
    from app.models import Download, User
    from app.services import cleanup

    login(client, USER)
    client.patch("/api/account", json={"email": None, "default_preset_id": None, "cleanup_days": 7})
    assert client.get("/api/account").json()["cleanup_days"] == 7

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=USER["username"]).one()
        folder = downloads_dir / user.username
        folder.mkdir(parents=True, exist_ok=True)
        rows = []
        for name, age in (("alt.mp4", 10), ("neu.mp4", 1)):
            (folder / name).write_bytes(b"x" * 100)
            rows.append(Download(user_id=user.id, url=f"https://example.com/{name}", title=name, options={},
                                 status="completed", file_path=f"{user.username}/{name}", file_size=100,
                                 created_at=now - timedelta(days=age), finished_at=now - timedelta(days=age)))
        db.add_all(rows)
        db.commit()
        old_id, new_id = rows[0].id, rows[1].id

    assert asyncio.run(cleanup.run_rules()) >= 1
    with SessionLocal() as db:
        assert db.get(Download, old_id) is None and db.get(Download, new_id) is not None
    assert not (folder / "alt.mp4").exists() and (folder / "neu.mp4").exists()

    # Too little free space: the oldest finished downloads go until there is room.
    client.patch("/api/account", json={"email": None, "default_preset_id": None, "clear_cleanup_days": True})
    login(client, ADMIN)
    client.put("/api/admin/settings", json={"cleanup_min_free_gb": 1})
    monkeypatch.setattr(cleanup.shutil, "disk_usage", lambda _path: type("U", (), {"free": cleanup.GB - 50})())
    try:
        asyncio.run(cleanup.run_rules())
        with SessionLocal() as db:
            assert db.get(Download, new_id) is None
    finally:
        client.put("/api/admin/settings", json={"clear_cleanup_min_free": True})
