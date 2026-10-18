from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .. import config
from ..database import get_db
from ..deps import current_user
from ..models import Download, Preset, User
from ..services import settings as app_settings
from ..services import ytdlp
from ..services.downloads import ACTIVE, manager, safe_component, serialize
from ..services.events import hub

router = APIRouter(prefix="/api", tags=["downloads"])


def _check_url(v: str) -> str:
    v = v.strip()
    if not v.lower().startswith(("http://", "https://")) or len(v) > 2048:
        raise ValueError("Bitte eine gültige http(s)-URL angeben")
    return v


class ProbeBody(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _check_url(v)


class Item(BaseModel):
    url: str
    video_id: str | None = None
    title: str | None = Field(None, max_length=1000)
    uploader: str | None = Field(None, max_length=255)
    thumbnail: str | None = Field(None, max_length=2048)
    duration: float | None = None
    index: int | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _check_url(v)


class CreateBody(BaseModel):
    preset_id: int
    items: list[Item] = Field(min_length=1)
    playlist_title: str | None = Field(None, max_length=500)
    own_folder: bool = True


class ClearBody(BaseModel):
    statuses: list[Literal["failed", "canceled", "completed"]] = ["failed", "canceled"]


def _visible_preset(db: Session, user: User, preset_id: int) -> Preset:
    preset = db.get(Preset, preset_id)
    if preset is None or preset.user_id not in (None, user.id):
        raise HTTPException(404, "Preset nicht gefunden")
    return preset


def _owned(db: Session, user: User, download_id: int) -> Download:
    d = db.get(Download, download_id)
    if d is None or (d.user_id != user.id and not user.is_admin):
        raise HTTPException(404, "Download nicht gefunden")
    return d


def _out(d: Download) -> dict:
    return serialize(d, manager.live(d.id))


@router.post("/probe")
async def probe(body: ProbeBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    max_items = int(app_settings.get(db, "max_playlist_items"))
    db.close()  # don't hold a connection while yt-dlp is working
    try:
        return await ytdlp.probe(body.url, max_items)
    except ytdlp.ProbeError as exc:
        raise HTTPException(422, str(exc))


@router.post("/downloads")
async def create(body: CreateBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    preset = _visible_preset(db, user, body.preset_id)
    max_items = int(app_settings.get(db, "max_playlist_items"))
    if len(body.items) > max_items:
        raise HTTPException(400, f"Höchstens {max_items} Einträge pro Auftrag")

    subfolder = safe_component(body.playlist_title) if body.playlist_title and body.own_folder else None
    rows = []
    for item in body.items:
        rows.append(Download(
            user_id=user.id, url=item.url, video_id=item.video_id, title=item.title or item.url,
            uploader=item.uploader, thumbnail=item.thumbnail, duration=item.duration,
            preset_name=preset.name, options=preset.options, subfolder=subfolder,
            playlist_title=body.playlist_title, playlist_index=item.index if body.playlist_title else None,
        ))
    db.add_all(rows)
    db.commit()
    for d in rows:
        await hub.publish("download", _out(d), user.id)
    manager.wake()
    return [_out(d) for d in rows]


@router.get("/downloads")
def list_downloads(
    view: Literal["queue", "library", "all"] = "all",
    q: str | None = None,
    scope: Literal["mine", "all"] = "mine",
    user_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Download).options(joinedload(Download.user))
    if scope == "all" and user.is_admin:
        if user_id is not None:
            query = query.filter(Download.user_id == user_id)
    else:
        query = query.filter(Download.user_id == user.id)

    if view == "queue":
        query = query.filter(Download.status.in_(("queued", *ACTIVE, "failed", "canceled")))
    elif view == "library":
        query = query.filter(Download.status == "completed")
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Download.title.ilike(like), Download.uploader.ilike(like), Download.playlist_title.ilike(like)))

    total = query.count()
    order = {
        "queue": Download.created_at.asc(),
        "library": Download.finished_at.desc(),
        "all": Download.created_at.desc(),
    }[view]
    rows = query.order_by(order, Download.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_out(d) for d in rows]}


@router.post("/downloads/{download_id}/cancel")
async def cancel(download_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, download_id)
    if d.status == "queued":
        d.status = "canceled"
        db.commit()
        await hub.publish("download", _out(d), d.user_id)
    elif d.status in ACTIVE:
        manager.cancel(d.id)  # the worker reports the final state
    else:
        raise HTTPException(409, "Download läuft nicht")
    return {"ok": True}


@router.post("/downloads/{download_id}/retry")
async def retry(download_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, download_id)
    if d.status not in ("failed", "canceled"):
        raise HTTPException(409, "Nur fehlgeschlagene oder abgebrochene Downloads können wiederholt werden")
    d.status, d.progress, d.error, d.finished_at = "queued", 0.0, None, None
    db.commit()
    await hub.publish("download", _out(d), d.user_id)
    manager.wake()
    return _out(d)


def _resolve_file(d: Download) -> Path | None:
    if not d.file_path:
        return None
    path = (config.DOWNLOAD_DIR / d.file_path).resolve()
    if not path.is_relative_to(config.DOWNLOAD_DIR) or not path.is_file():
        return None
    return path


def _delete_file(d: Download) -> None:
    path = _resolve_file(d)
    if path is None:
        return
    path.unlink(missing_ok=True)
    # Remove an emptied playlist folder, but never the user's root folder.
    parent = path.parent
    root = (config.DOWNLOAD_DIR / d.user.username).resolve()
    if parent != root and parent.is_relative_to(root) and not any(parent.iterdir()):
        parent.rmdir()


@router.delete("/downloads/{download_id}")
async def delete(
    download_id: int, delete_file: bool = True, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    d = _owned(db, user, download_id)
    if d.status in ACTIVE:
        raise HTTPException(409, "Laufende Downloads zuerst abbrechen")
    if delete_file:
        _delete_file(d)
    owner = d.user_id
    db.delete(d)
    db.commit()
    await hub.publish("download_removed", {"id": download_id}, owner)
    return {"ok": True}


@router.post("/downloads/clear")
async def clear(body: ClearBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Removes finished entries from the list. Completed files stay on disk."""
    rows = db.query(Download).filter(Download.user_id == user.id, Download.status.in_(body.statuses)).all()
    ids = [d.id for d in rows]
    for d in rows:
        db.delete(d)
    db.commit()
    for download_id in ids:
        await hub.publish("download_removed", {"id": download_id}, user.id)
    return {"removed": len(ids)}


@router.get("/downloads/{download_id}/file")
def file(download_id: int, inline: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, download_id)
    path = _resolve_file(d) if d.status == "completed" else None
    if path is None:
        raise HTTPException(404, "Datei nicht vorhanden")
    return FileResponse(path, filename=path.name, content_disposition_type="inline" if inline else "attachment")


