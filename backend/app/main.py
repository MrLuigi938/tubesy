import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config
from .database import Base, SessionLocal, engine
from .models import Preset, User
from .routers import account, admin, auth, downloads, presets, ws
from .security import hash_password
from .services import ytdlp
from .services.downloads import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("tubevault")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _seed() -> None:
    with SessionLocal() as db:
        if db.query(Preset).filter(Preset.user_id.is_(None)).count() == 0:
            db.add_all(Preset(user_id=None, name=name, options=opts) for name, opts in ytdlp.BUILTIN_PRESETS)
        if config.ADMIN_USERNAME and config.ADMIN_PASSWORD and db.query(User).count() == 0:
            db.add(User(username=config.ADMIN_USERNAME.lower(), password_hash=hash_password(config.ADMIN_PASSWORD), role="admin"))
            log.info("Admin-Konto '%s' aus Umgebungsvariablen angelegt", config.ADMIN_USERNAME)
        db.commit()


async def _auto_update() -> None:
    try:
        log.info("yt-dlp aktualisiert: %s", await ytdlp.self_update())
    except Exception as exc:  # offline or read-only image: keep the bundled version
        log.warning("yt-dlp-Update fehlgeschlagen: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.ensure_dirs()
    Base.metadata.create_all(engine)
    _seed()
    if config.YTDLP_AUTO_UPDATE:
        asyncio.create_task(_auto_update())
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(title="TubeVault", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CSRF: browsers cannot add custom headers to cross-site form posts, and a
    # cross-site fetch with one triggers a CORS preflight that we never allow.
    if request.method in UNSAFE_METHODS and request.url.path.startswith("/api/"):
        if request.headers.get("x-requested-with") != "TubeVault":
            return JSONResponse({"detail": "CSRF-Prüfung fehlgeschlagen"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' https: data:; media-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    return response


for module in (auth, account, downloads, presets, admin, ws):
    app.include_router(module.router)


@app.get("/api/health", include_in_schema=False)
def health():
    return {"ok": True}


@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    """Serves the Svelte build; unknown non-API paths get index.html for client-side routing."""
    path = request.url.path
    if exc.status_code == 404 and request.method == "GET" and not path.startswith("/api/"):
        root = config.FRONTEND_DIR.resolve()
        candidate = (root / path.lstrip("/")).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            cache = "public, max-age=31536000, immutable" if "/_app/immutable/" in path else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))
