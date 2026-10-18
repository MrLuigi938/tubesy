import time

from fastapi.testclient import TestClient

ADMIN = {"username": "chef", "password": "sehr-geheim-123"}
FRIEND = {"username": "kollege", "password": "auch-geheim-456"}


def wait_for(client, download_id, statuses=("completed", "failed", "canceled"), timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        items = client.get("/api/downloads").json()["items"]
        d = next(i for i in items if i["id"] == download_id)
        if d["status"] in statuses:
            return d
        time.sleep(0.3)
    raise AssertionError(f"download {download_id} stuck in {d['status']}")


def login(client, creds):
    client.cookies.clear()
    r = client.post("/api/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return r.json()


def test_full_flow(client: TestClient, media_url, downloads_dir):
    # -- first start: setup wizard ------------------------------------------
    assert client.get("/api/status").json()["needs_setup"] is True
    assert client.get("/api/auth/me").status_code == 401
    r = client.post("/api/setup", json=ADMIN)
    assert r.status_code == 200 and r.json()["role"] == "admin"
    assert client.post("/api/setup", json=ADMIN).status_code == 409

    # -- CSRF header is mandatory for state-changing requests ---------------
    r = client.post("/api/auth/login", json=ADMIN, headers={"X-Requested-With": ""})
    assert r.status_code == 403

    # -- registration is invite-only by default -----------------------------
    client.cookies.clear()
    assert client.post("/api/auth/register", json=FRIEND).status_code == 403
    login(client, ADMIN)
    token = client.post("/api/admin/invites", json={"note": "Kollege", "max_uses": 1}).json()["token"]
    client.cookies.clear()
    assert client.get(f"/api/status?invite={token}").json()["invite_valid"] is True
    r = client.post("/api/auth/register", json={**FRIEND, "invite": token})
    assert r.status_code == 200 and r.json()["role"] == "user"
    client.cookies.clear()
    r = client.post("/api/auth/register", json={"username": "dritter", "password": "x" * 12, "invite": token})
    assert r.status_code == 400  # invite used up

    # -- normal users cannot reach the admin API ----------------------------
    login(client, FRIEND)
    assert client.get("/api/admin/users").status_code == 403

    # -- probe + download ----------------------------------------------------
    info = client.post("/api/probe", json={"url": media_url}).json()
    assert info["type"] == "video" and info["video_id"] == "clip"
    presets = client.get("/api/presets").json()["items"]
    mp4 = next(p for p in presets if p["name"] == "Beste Qualität (MP4)")
    audio = next(p for p in presets if p["name"] == "Audio (MP3)")

    created = client.post("/api/downloads", json={"preset_id": mp4["id"], "items": [{"url": media_url, "title": "Clip"}]}).json()
    d = wait_for(client, created[0]["id"])
    assert d["status"] == "completed", d["error"]
    assert d["filename"].endswith(".mp4") and d["file_size"] > 0
    assert (downloads_dir / "kollege" / d["filename"]).is_file()

    r = client.get(f"/api/downloads/{d['id']}/file")
    assert r.status_code == 200 and r.headers["content-disposition"].startswith("attachment")
    r = client.get(f"/api/downloads/{d['id']}/file?inline=1", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100

    # -- playlist items land in their own folder, numbered ------------------
    created = client.post("/api/downloads", json={
        "preset_id": audio["id"], "playlist_title": "Meine: Liste?",
        "items": [{"url": media_url, "title": "Eins", "index": 1}, {"url": media_url + "?2", "title": "Zwei", "index": 2}],
    }).json()
    for c in created:
        done = wait_for(client, c["id"])
        assert done["status"] == "completed", done["error"]
    folder = downloads_dir / "kollege" / "Meine_ Liste_"
    assert sorted(p.name[:6] for p in folder.iterdir()) == ["001 - ", "002 - "]
    assert all(p.suffix == ".mp3" for p in folder.iterdir())

    # -- failures are reported with yt-dlp's message ------------------------
    bad = client.post("/api/downloads", json={"preset_id": mp4["id"], "items": [{"url": media_url.replace("clip", "missing")}]}).json()[0]
    bad = wait_for(client, bad["id"])
    assert bad["status"] == "failed" and "404" in bad["error"]

    # -- data separation -----------------------------------------------------
    friend_id = d["id"]
    login(client, ADMIN)
    assert all(i["user_id"] != d["user_id"] for i in client.get("/api/downloads").json()["items"])
    all_items = client.get("/api/downloads?scope=all").json()["items"]
    assert any(i["id"] == friend_id and i["username"] == "kollege" for i in all_items)
    users = {u["username"]: u for u in client.get("/api/admin/users").json()}
    assert users["kollege"]["downloads"] == 3 and users["kollege"]["used_bytes"] > 0

    # Admin creates a second normal user, who must not see the friend's files.
    client.post("/api/admin/users", json={"username": "fremder", "password": "fremd-passwort-1"})
    login(client, {"username": "fremder", "password": "fremd-passwort-1"})
    assert client.get(f"/api/downloads/{friend_id}/file").status_code == 404
    assert client.delete(f"/api/downloads/{friend_id}").status_code == 404

    # -- quota ---------------------------------------------------------------
    login(client, ADMIN)
    client.patch(f"/api/admin/users/{users['kollege']['id']}", json={"quota_gb": 0})
    login(client, FRIEND)
    q = client.post("/api/downloads", json={"preset_id": mp4["id"], "items": [{"url": media_url}]}).json()[0]
    q = wait_for(client, q["id"])
    assert q["status"] == "failed" and "kontingent" in q["error"].lower()

    # -- delete removes the file and an emptied playlist folder -------------
    lib = client.get("/api/downloads?view=library").json()["items"]
    for item in lib:
        assert client.delete(f"/api/downloads/{item['id']}").status_code == 200
    assert not folder.exists()
    assert client.post("/api/downloads/clear", json={}).json()["removed"] == 2

    # -- deactivating a user ends their sessions ----------------------------
    login(client, ADMIN)
    client.patch(f"/api/admin/users/{users['kollege']['id']}", json={"is_active": False})
    client.cookies.clear()
    assert client.post("/api/auth/login", json=FRIEND).status_code == 401

    # -- the last admin is protected ----------------------------------------
    login(client, ADMIN)
    me = client.get("/api/auth/me").json()
    assert client.patch(f"/api/admin/users/{me['id']}", json={"role": "user"}).status_code == 409


def test_cancel_running_download(client: TestClient, slow_url):
    login(client, ADMIN)
    preset = client.get("/api/presets").json()["items"][0]
    d = client.post("/api/downloads", json={"preset_id": preset["id"], "items": [{"url": slow_url}]}).json()[0]
    running = wait_for(client, d["id"], statuses=("downloading",), timeout=20)
    assert running["status"] == "downloading"
    assert client.post(f"/api/downloads/{d['id']}/cancel").status_code == 200
    done = wait_for(client, d["id"], timeout=20)
    assert done["status"] == "canceled"
    # partial files live in a per-download temp dir that is removed afterwards
    from app import config
    assert not (config.TEMP_DIR / str(d["id"])).exists()
    # and it can be retried
    assert client.post(f"/api/downloads/{d['id']}/retry").json()["status"] == "queued"
    client.post(f"/api/downloads/{d['id']}/cancel")


def test_websocket_origin_check(client: TestClient):
    from starlette.websockets import WebSocketDisconnect

    login(client, ADMIN)
    # Behind a proxy the Host header often lacks the port of the public origin.
    with client.websocket_connect("/api/ws", headers={"origin": "https://testserver:8443"}) as ws:
        ws.send_text("ping")
    try:
        with client.websocket_connect("/api/ws", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_text()
        raise AssertionError("foreign origin was accepted")
    except WebSocketDisconnect as exc:
        assert exc.code == 4403


def test_playlists_zip_and_delete(client: TestClient, media_url):
    import io
    import zipfile

    login(client, ADMIN)
    preset = next(p for p in client.get("/api/presets").json()["items"] if p["name"] == "Audio (MP3)")
    items = [{"url": f"{media_url}?{i}", "title": f"Lied {i}", "index": i} for i in (1, 2)]
    created = client.post("/api/downloads", json={"preset_id": preset["id"], "items": items, "playlist_title": "Sommer"}).json()
    for c in created:
        assert wait_for(client, c["id"])["status"] == "completed"
    single = client.post("/api/downloads", json={"preset_id": preset["id"], "items": [{"url": media_url + "?solo"}]}).json()[0]
    wait_for(client, single["id"])

    playlists = {p["title"]: p for p in client.get("/api/playlists").json()}
    assert playlists["Sommer"]["count"] == 2 and playlists["Sommer"]["total_size"] > 0
    in_list = client.get("/api/downloads", params={"view": "library", "playlist": "Sommer"}).json()["items"]
    assert [d["playlist_index"] for d in in_list] == [1, 2]
    solo = client.get("/api/downloads", params={"view": "library", "standalone": True}).json()["items"]
    assert all(d["playlist_title"] is None for d in solo) and any(d["id"] == single["id"] for d in solo)

    r = client.get("/api/playlists/zip", params={"title": "Sommer"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(names) == 2 and names[0].startswith("001 - ") and names[1].startswith("002 - ")
    assert zipfile.ZipFile(io.BytesIO(r.content)).testzip() is None

    assert client.delete("/api/playlists", params={"title": "Sommer"}).json()["removed"] == 2
    assert "Sommer" not in {p["title"] for p in client.get("/api/playlists").json()}


def test_api_keys_and_dashboard_api(client: TestClient, media_url):
    login(client, ADMIN)
    read = client.post("/api/account/tokens", json={"name": "HeimDeck", "scope": "read"}).json()
    full = client.post("/api/account/tokens", json={"name": "Kurzbefehl", "scope": "full"}).json()
    assert read["key"].startswith("tsy_") and "key" not in client.get("/api/account/tokens").json()[0]

    client.cookies.clear()
    bare = TestClient(client.app)  # no CSRF header, no cookie: like an external tool
    assert bare.get("/api/v1/stats").status_code == 401
    assert bare.get("/api/v1/stats", headers={"X-Api-Key": "tsy_falsch"}).status_code == 401
    st = bare.get("/api/v1/stats", headers={"X-Api-Key": read["key"]}).json()
    assert st["user"]["username"] == "chef" and "instance" in st and "completed" in st["downloads"]
    assert isinstance(bare.get("/api/v1/queue", headers={"Authorization": f"Bearer {read['key']}"}).json(), list)

    # read-only keys cannot start downloads, full keys can (without CSRF header)
    assert bare.post("/api/v1/download", json={"url": media_url}, headers={"X-Api-Key": read["key"]}).status_code == 403
    r = bare.post("/api/v1/download", json={"url": media_url + "?api", "preset": "Audio (MP3)"}, headers={"X-Api-Key": full["key"]})
    assert r.status_code == 200 and r.json()["queued"] == 1 and r.json()["preset"] == "Audio (MP3)"

    # keys cannot manage the account
    assert bare.get("/api/account/tokens", headers={"X-Api-Key": full["key"]}).status_code == 403

    login(client, ADMIN)
    assert client.delete(f"/api/account/tokens/{read['id']}").status_code == 200
    assert bare.get("/api/v1/stats", headers={"X-Api-Key": read["key"]}).status_code == 401


def test_password_policy(client: TestClient):
    login(client, ADMIN)
    assert client.get("/api/status").json()["min_password_length"] == 6
    assert client.post("/api/admin/users", json={"username": "kurz", "password": "12345"}).status_code == 422
    assert client.post("/api/admin/users", json={"username": "kurz", "password": "123456"}).status_code == 200
    client.put("/api/admin/settings", json={"min_password_length": 10})
    assert client.get("/api/status").json()["min_password_length"] == 10
    r = client.post("/api/admin/users", json={"username": "kurz2", "password": "1234567"})
    assert r.status_code == 400 and "10" in r.json()["detail"]
    # admins only need the hard minimum
    assert client.post("/api/admin/users", json={"username": "admin2", "password": "1234567", "role": "admin"}).status_code == 200
    client.put("/api/admin/settings", json={"min_password_length": 6})


def test_supported_sites(client: TestClient):
    login(client, ADMIN)
    sites = client.get("/api/extractors").json()["sites"]
    assert len(sites) > 500 and "youtube" in [s.lower() for s in sites] and "generic" not in sites


def test_login_rate_limit(client: TestClient):
    client.cookies.clear()
    codes = [client.post("/api/auth/login", json={"username": "chef", "password": "falsch"}).status_code for _ in range(9)]
    assert codes[:8] == [401] * 8 and codes[8] == 429
