import os
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="tubesy-test-"))
os.environ.update({
    "CONFIG_DIR": str(_tmp / "config"),
    "DOWNLOAD_DIR": str(_tmp / "downloads"),
    "YTDLP_AUTO_UPDATE": "false",
    "YTDLP_PYTHON": sys.executable,
    "FRONTEND_DIR": str(_tmp / "static"),
})


@pytest.fixture(scope="session")
def media_url():
    """Serves a short generated video over HTTP, so downloads run without internet access."""
    media = _tmp / "media"
    media.mkdir()
    clip = media / "clip.mp4"
    ret = os.system(
        f"ffmpeg -loglevel error -y -f lavfi -i testsrc=duration=3:size=320x240:rate=10 "
        f"-f lavfi -i sine=duration=3 -c:v libx264 -c:a aac -shortest {clip}"
    )
    assert ret == 0, "ffmpeg is required for the tests"
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(media)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/clip.mp4"
    server.shutdown()


class _SlowHandler(SimpleHTTPRequestHandler):
    """Trickles a large file so a download stays running long enough to cancel it."""

    def do_GET(self):
        size = 50 * 1024 * 1024
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        try:
            for _ in range(size // 65536):
                self.wfile.write(b"\0" * 65536)
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def slow_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SlowHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/slow.mp4"
    server.shutdown()


@pytest.fixture(scope="session")
def client():
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, headers={"X-Requested-With": "Tubesy"}) as c:
        yield c


@pytest.fixture(scope="session")
def downloads_dir() -> Path:
    return Path(os.environ["DOWNLOAD_DIR"])
