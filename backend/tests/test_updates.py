from pathlib import Path

from fastapi.testclient import TestClient

from app.services.updates import newest_release, parse_version


def rel(tag, prerelease=False, draft=False):
    return {"tag_name": tag, "prerelease": prerelease, "draft": draft,
            "html_url": f"https://github.com/MrLuigi938/tubesy/releases/tag/{tag}", "published_at": "2026-10-01T10:00:00Z"}


def test_version_order():
    v = parse_version
    assert v("v1.2.0").newer(v("1.1.9"))
    assert v("1.10.0").newer(v("1.9.0"))
    assert v("1.0.0").newer(v("1.0.0-beta.3"))
    assert v("1.0.0-beta.10").newer(v("1.0.0-beta.2"))
    assert v("1.0.0-rc.1").newer(v("1.0.0-beta.9"))
    assert not v("1.0.0").newer(v("1.0.0"))
    assert v("dev") is None and v("edge-1a2b3c4") is None and v("1.0") is None


def test_newest_release():
    releases = [rel("v1.2.0-beta.1", prerelease=True), rel("v1.1.0"), rel("v1.0.1"), rel("v2.0.0", draft=True), rel("nightly")]
    # Stable installs only see stable releases.
    assert newest_release(releases, "1.0.0")["version"] == "1.1.0"
    assert newest_release(releases, "1.1.0") is None
    # A beta also sees newer betas.
    assert newest_release(releases, "1.1.0-beta.1")["version"] == "1.2.0-beta.1"
    # Builds without a version never offer anything.
    assert newest_release(releases, "dev") is None
    assert newest_release(releases, "edge-1a2b3c4") is None


def test_info_and_non_media_file(client: TestClient, downloads_dir: Path):
    from app.database import SessionLocal
    from app.models import Download, User

    from app.security import login_ip_limiter, login_user_limiter
    from test_flow import ADMIN, login

    # test_login_rate_limit leaves the test client's address blocked.
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, ADMIN)
    info = client.get("/api/info").json()
    assert info["version"] == "dev" and info["update"] is None
    assert client.get("/api/admin/settings").json()["update_check"] is True

    # A downloaded HTML file must never be shown in the browser.
    with SessionLocal() as db:
        admin = db.query(User).filter_by(username=ADMIN["username"]).one()
        (downloads_dir / admin.username).mkdir(parents=True, exist_ok=True)
        (downloads_dir / admin.username / "page.html").write_text("<script>alert(1)</script>")
        d = Download(user_id=admin.id, url="https://example.com/page.html", title="page", options={},
                     status="completed", file_path=f"{admin.username}/page.html", file_size=25)
        db.add(d)
        db.commit()
        download_id = d.id
    r = client.get(f"/api/downloads/{download_id}/file?inline=1")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("attachment")
    assert r.headers["content-type"] == "application/octet-stream"


def test_thumbnail_conversion_before_download_is_not_processing(client: TestClient):
    """yt-dlp converts thumbnails before the download; the row must still say 'downloading'."""
    import asyncio

    from app.database import SessionLocal
    from app.models import Download, User
    from app.services.downloads import manager
    from test_flow import ADMIN

    class FakeProc:
        def __init__(self, lines):
            self.stdout = self._gen(lines)

        @staticmethod
        async def _gen(lines):
            for line in lines:
                yield (line + "\n").encode()

    lines = [
        "TSPOST:started|ThumbnailsConvertor",
        "TSPOST:finished|ThumbnailsConvertor",
        "TSPROG:downloading|250|1000|NA|100|7|mp4",
    ]
    with SessionLocal() as db:
        admin = db.query(User).filter_by(username=ADMIN["username"]).one()
        d = Download(user_id=admin.id, url="https://example.com/v", title="v", options={}, status="downloading")
        db.add(d)
        db.commit()
        manager._live[d.id] = {}
        try:
            asyncio.run(manager._consume(d, FakeProc(lines)))
            assert d.status == "downloading"
            assert manager.live(d.id)["progress"] == 25.0
        finally:
            manager._live.pop(d.id, None)
            db.delete(d)
            db.commit()


def test_cli_reset_password(client: TestClient):
    from app.cli import main
    from app.security import login_ip_limiter, login_user_limiter
    from test_flow import ADMIN, login

    assert main(["reset-password", ADMIN["username"], "x"]) == 1  # too short
    assert main(["reset-password", "nobody", "neues-passwort-1"]) == 1
    assert main(["reset-password", ADMIN["username"].upper(), "neues-passwort-1"]) == 0
    login_ip_limiter._hits.clear()
    login_user_limiter._hits.clear()
    login(client, {"username": ADMIN["username"], "password": "neues-passwort-1"})
    assert main(["reset-password", ADMIN["username"], ADMIN["password"]]) == 0
