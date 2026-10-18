"""Runtime configuration, read once from environment variables."""
import os
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/config")).resolve()
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/downloads")).resolve()
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", Path(__file__).resolve().parent.parent / "static"))
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{CONFIG_DIR / 'tubesy.db'}")

# "auto" sets the Secure flag when the request arrived via https (also behind a proxy).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "auto").lower()
SESSION_COOKIE = "tubesy_session"

YTDLP_AUTO_UPDATE = _bool("YTDLP_AUTO_UPDATE", True)
YTDLP_PYTHON = os.environ.get("YTDLP_PYTHON", "python3")

# Optional admin bootstrap (otherwise the setup wizard is shown on first start).
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

CACHE_DIR = CONFIG_DIR / "cache"
TEMP_DIR = Path(os.environ.get("TEMP_DIR", CONFIG_DIR / "tmp")).resolve()


def ensure_dirs() -> None:
    for path in (CONFIG_DIR, DOWNLOAD_DIR, CACHE_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
