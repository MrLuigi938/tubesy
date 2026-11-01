"""Version 1.1: hidden videos, download anyway, batch actions, clean-up, quota, local addresses."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.security import login_ip_limiter, login_user_limiter
from test_flow import ADMIN, login, wait_for

USER = {"username": "nutzerin", "password": "nutzer-passwort-11"}


@pytest.fixture(autouse=True)
def _no_rate_limit():
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()


@pytest.fixture(scope="module", autouse=True)
def _user(client):
    """A normal user of its own (the flow test locks its user at the end)."""
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, ADMIN)
    client.post("/api/admin/users", json=USER)


def audio_preset(client) -> int:
    return next(p for p in client.get("/api/presets").json()["items"] if p["name"] == "Audio (MP3)")["id"]


def queue(client, url, **extra) -> dict:
    r = client.post("/api/downloads", json={"preset_id": audio_preset(client), "items": [{"url": url}], **extra})
    assert r.status_code == 200, r.text
    return r.json()[0]


def test_local_addresses_need_permission(client: TestClient, media_url):
    login(client, ADMIN)
    client.put("/api/admin/settings", json={"allow_local_urls": False})
    try:
        login(client, USER)
        assert client.post("/api/probe", json={"url": media_url}).status_code == 403
        r = client.post("/api/downloads", json={"preset_id": audio_preset(client), "items": [{"url": media_url}]})
        assert r.status_code == 403 and "lokalen" in r.json()["detail"]
        # Administrators may always.
        login(client, ADMIN)
        assert client.post("/api/probe", json={"url": media_url}).status_code == 200
    finally:
        login(client, ADMIN)
        client.put("/api/admin/settings", json={"allow_local_urls": True})


def test_download_anyway_gets_the_real_title(client: TestClient, media_url):
    """Queued with nothing but the link (after a failed check), the title comes from yt-dlp."""
    login(client, USER)
    d = queue(client, media_url + "?anyway")
    assert d["title"].endswith("?anyway")
    done = wait_for(client, d["id"])
    assert done["status"] == "completed" and done["title"] == "clip"


def test_hidden_videos(client: TestClient, media_url, slow_url):
    login(client, USER)
    d = queue(client, media_url + "?hidden", hidden=True)
    assert d["hidden"] is True and d["title"] is None and d["thumbnail"] is None
    done = wait_for(client, d["id"])
    assert done["status"] == "completed" and done["title"] is None and done["filename"] is None

    library = client.get("/api/downloads?view=library&hidden=exclude").json()["items"]
    assert d["id"] not in [x["id"] for x in library]
    hidden = client.get("/api/downloads?view=library&hidden=only").json()["items"]
    assert [x["id"] for x in hidden] == [d["id"]]

    # Tap to reveal: everything comes back for this one request.
    revealed = client.get(f"/api/downloads/{d['id']}").json()
    assert revealed["title"] == "clip" and revealed["filename"].endswith(".mp3")

    # Dashboards never see it in the library, and only a placeholder in the queue.
    key = client.post("/api/account/tokens", json={"name": "dash", "scope": "read"}).json()["key"]
    bare = TestClient(client.app)
    items = bare.get("/api/downloads?view=library&hidden=include", headers={"X-Api-Key": key}).json()["items"]
    assert d["id"] not in [x["id"] for x in items]
    running = queue(client, slow_url + "?hidden", hidden=True)
    shown = bare.get("/api/v1/queue", headers={"X-Api-Key": key}).json()
    entry = next(x for x in shown if x["id"] == running["id"])
    assert entry["title"] in ("Ausgeblendetes Video", "Hidden video") and entry["thumbnail"] is None
    client.post(f"/api/downloads/{running['id']}/cancel")
    wait_for(client, running["id"])

    # Show it again.
    r = client.patch(f"/api/downloads/{d['id']}", json={"hidden": False})
    assert r.json()["hidden"] is False and r.json()["title"] == "clip"


def test_auto_hide_adult_follows_the_account_setting(client: TestClient):
    from app.database import SessionLocal
    from app.models import Download, User
    from app.services.downloads import manager

    login(client, USER)
    assert client.get("/api/account").json()["auto_hide_adult"] is True
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=USER["username"]).one()
        adult = Download(user=user, url="https://example.com/a", title="https://example.com/a", options={})
        manager._apply_meta(adult, {"title": "Film", "age_limit": 18})
        assert adult.hidden is True and adult.title == "Film" and adult.age_limit == 18
        teen = Download(user=user, url="https://example.com/b", title="b", options={})
        manager._apply_meta(teen, {"age_limit": 12})
        assert not teen.hidden
        db.rollback()

    client.patch("/api/account", json={"email": None, "default_preset_id": None, "auto_hide_adult": False})
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=USER["username"]).one()
        adult = Download(user=user, url="https://example.com/c", title="c", options={})
        manager._apply_meta(adult, {"age_limit": 18})
        assert not adult.hidden
        db.rollback()
    client.patch("/api/account", json={"email": None, "default_preset_id": None, "auto_hide_adult": True})


def test_batch_zip_and_clean_up(client: TestClient, media_url):
    login(client, USER)
    ids = [wait_for(client, queue(client, f"{media_url}?batch{i}")["id"])["id"] for i in range(2)]

    r = client.post("/api/downloads/batch", json={"ids": ids, "action": "hide"})
    assert r.json() == {"done": 2, "skipped": 0}
    assert all(client.get(f"/api/downloads/{i}").json()["hidden"] for i in ids)
    client.post("/api/downloads/batch", json={"ids": ids, "action": "show"})

    url = client.post("/api/zip", json={"ids": ids}).json()["url"]
    archive = zipfile.ZipFile(io.BytesIO(client.get(url).content))
    assert len(archive.namelist()) == 2
    # The link belongs to the user who asked for it.
    login(client, ADMIN)
    assert client.get(url).status_code == 404

    login(client, USER)
    r = client.post("/api/downloads/batch", json={"ids": [ids[0]], "action": "delete", "delete_files": True})
    assert r.json()["done"] == 1

    count = client.post("/api/downloads/cleanup", json={"scope": "videos"}).json()
    assert count["videos"] >= 1 and count["bytes"] > 0
    left = client.get("/api/downloads?view=library").json()["total"]
    assert left >= 1  # dry run deletes nothing
    done = client.post("/api/downloads/cleanup", json={"scope": "all", "dry_run": False}).json()
    assert done["removed"] >= 1
    assert client.get("/api/downloads?view=all").json()["total"] == 0


def test_quota_is_checked_during_the_download(client: TestClient, slow_url):
    login(client, ADMIN)
    friend = next(u for u in client.get("/api/admin/users").json() if u["username"] == USER["username"])
    client.patch(f"/api/admin/users/{friend['id']}", json={"quota_gb": 0.001})  # about 1 MB
    try:
        login(client, USER)
        d = wait_for(client, queue(client, slow_url + "?quota")["id"], timeout=30)
        assert d["status"] == "failed" and d["error"] == "Speicherkontingent würde überschritten"
    finally:
        login(client, ADMIN)
        client.patch(f"/api/admin/users/{friend['id']}", json={"clear_quota": True})
