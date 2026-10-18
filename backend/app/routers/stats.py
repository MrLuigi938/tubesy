"""Small, stable API for dashboards (HeimDeck, Homepage, …) and automations.

Authenticate with an API key from the account page:
    X-Api-Key: tsy_…      or      Authorization: Bearer tsy_…
"""
import shutil
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import current_user
from ..models import Download, Preset, User
from ..services import settings as app_settings
from ..services import ytdlp
from ..services.downloads import ACTIVE, manager, serialize, used_bytes
from ..services.events import hub
from .downloads import _check_url

router = APIRouter(prefix="/api/v1", tags=["dashboard api"])


@router.get("/stats")
def stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Counts for the caller; admins additionally get instance-wide numbers."""

    def counts(user_id: int | None) -> dict:
        q = db.query(Download.status, func.count(Download.id))
        if user_id is not None:
            q = q.filter(Download.user_id == user_id)
        by_status = dict(q.group_by(Download.status).all())
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        done_today = db.query(func.count(Download.id)).filter(
            Download.status == "completed", Download.finished_at >= since,
            *([Download.user_id == user_id] if user_id is not None else []),
        ).scalar()
        return {
            "queued": by_status.get("queued", 0),
            "active": sum(by_status.get(s, 0) for s in ACTIVE),
            "completed": by_status.get("completed", 0),
            "failed": by_status.get("failed", 0),
            "completed_24h": done_today or 0,
        }

    active_rows = (
        db.query(Download).filter(Download.status.in_(ACTIVE), Download.user_id == user.id).all()
        if not user.is_admin else db.query(Download).filter(Download.status.in_(ACTIVE)).all()
    )
    speed = sum((manager.live(d.id) or {}).get("speed") or 0 for d in active_rows)

    result = {
        "user": {"username": user.username, "role": user.role},
        "downloads": counts(user.id),
        "storage": {"used_bytes": used_bytes(db, user.id), "quota_bytes": user.quota_bytes},
        "speed_bytes": speed,
    }
    if user.is_admin:
        disk = shutil.disk_usage(config.DOWNLOAD_DIR)
        total_used = db.query(func.coalesce(func.sum(Download.file_size), 0)).filter(Download.status == "completed").scalar()
        result["instance"] = {
            "downloads": counts(None),
            "users": db.query(User).count(),
            "used_bytes": int(total_used or 0),
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
        }
    return result


@router.get("/queue")
def queue(limit: int = 10, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Running and waiting downloads (admins: of all users), running ones first."""
    q = db.query(Download).filter(Download.status.in_(("queued", *ACTIVE)))
    if not user.is_admin:
        q = q.filter(Download.user_id == user.id)
    rows = q.order_by(Download.status != "downloading", Download.created_at).limit(max(1, min(limit, 100))).all()
    return [serialize(d, manager.live(d.id)) for d in rows]


class QuickDownload(BaseModel):
    url: str
    preset: str | int | None = Field(None, description="Preset-ID oder -Name; leer = Standard-Preset")

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _check_url(v)


@router.post("/download")
async def quick_download(body: QuickDownload, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Queues a URL in one call: videos directly, playlists completely (in their own folder)."""
    visible = db.query(Preset).filter((Preset.user_id.is_(None)) | (Preset.user_id == user.id))
    if body.preset is None:
        preset = visible.filter(Preset.id == user.default_preset_id).first() or visible.order_by(Preset.id).first()
    elif isinstance(body.preset, int) or str(body.preset).isdigit():
        preset = visible.filter(Preset.id == int(body.preset)).first()
    else:
        preset = visible.filter(func.lower(Preset.name) == str(body.preset).lower()).first()
    if preset is None:
        raise HTTPException(404, "Preset nicht gefunden")

    max_items = int(app_settings.get(db, "max_playlist_items"))
    preset_name, options, user_id = preset.name, preset.options, user.id
    db.close()  # yt-dlp can take a while; don't hold the connection
    try:
        info = await ytdlp.probe(body.url, max_items)
    except ytdlp.ProbeError as exc:
        raise HTTPException(422, str(exc))

    from ..database import SessionLocal
    from ..services.downloads import safe_component

    with SessionLocal() as s:
        if info["type"] == "playlist":
            title = info["title"] or "Playlist"
            rows = [
                Download(user_id=user_id, url=e["url"], video_id=e["video_id"], title=e["title"], uploader=e["uploader"],
                         thumbnail=e["thumbnail"], duration=e["duration"], preset_name=preset_name, options=options,
                         subfolder=safe_component(title), playlist_title=title, playlist_index=e["index"])
                for e in info["entries"]
            ]
        else:
            rows = [Download(user_id=user_id, url=info["url"], video_id=info.get("video_id"), title=info["title"] or info["url"],
                             uploader=info["uploader"], thumbnail=info["thumbnail"], duration=info.get("duration"),
                             preset_name=preset_name, options=options)]
        s.add_all(rows)
        s.commit()
        out = [serialize(d) for d in rows]
    for d in out:
        await hub.publish("download", d, user_id)
    manager.wake()
    return {"type": info["type"], "title": info["title"], "queued": len(out), "preset": preset_name}
