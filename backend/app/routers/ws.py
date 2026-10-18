from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from urllib.parse import urlsplit

from .. import config
from ..database import SessionLocal
from ..deps import resolve_session
from ..services.events import Client, hub

router = APIRouter()


@router.websocket("/api/ws")
async def events(ws: WebSocket):
    # Browsers send cookies on cross-site WebSocket handshakes, so the origin must be checked.
    origin = ws.headers.get("origin")
    if origin and urlsplit(origin).netloc != ws.headers.get("host"):
        await ws.close(code=4403)
        return
    with SessionLocal() as db:
        sess = resolve_session(db, ws.cookies.get(config.SESSION_COOKIE))
        if sess is None:
            await ws.close(code=4401)
            return
        client = Client(ws=ws, user_id=sess.user_id, is_admin=sess.user.is_admin)

    await ws.accept()
    hub.add(client)
    try:
        while True:
            await ws.receive_text()  # keep-alive pings from the browser
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(client)
