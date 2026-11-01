import mimetypes
import secrets
import time
import zipfile
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from .. import config
from ..database import get_db
from ..deps import api_key_from, current_user
from ..models import Download, Preset, User
from ..services import settings as app_settings
from ..services import ytdlp
from ..services.downloads import ACTIVE, ADULT_AGE, FINISHED, manager, safe_component, serialize
from ..services.events import hub
from ..services.netcheck import ensure_allowed

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
    age_limit: int | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return _check_url(v)


class CreateBody(BaseModel):
    preset_id: int
    items: list[Item] = Field(min_length=1)
    playlist_title: str | None = Field(None, max_length=500)
    own_folder: bool = True
    hidden: bool = False


class ClearBody(BaseModel):
    statuses: list[Literal["failed", "canceled", "completed"]] = ["failed", "canceled"]


class HiddenBody(BaseModel):
    hidden: bool


class BatchBody(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=5000)
    action: Literal["delete", "hide", "show"]
    delete_files: bool = True


class PlaylistBatchBody(BaseModel):
    titles: list[str] = Field(min_length=1, max_length=500)
    action: Literal["delete", "hide", "show"]
    delete_files: bool = True


class CleanupBody(BaseModel):
    scope: Literal["videos", "playlists", "all"]
    delete_files: bool = True
    dry_run: bool = True


class ZipBody(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=5000)
    playlists: list[str] = Field(default_factory=list, max_length=500)


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
    await ensure_allowed(db, user, [body.url])
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
    await ensure_allowed(db, user, [item.url for item in body.items])

    subfolder = safe_component(body.playlist_title) if body.playlist_title and body.own_folder else None
    rows = []
    for item in body.items:
        adult = (item.age_limit or 0) >= ADULT_AGE and user.auto_hide_adult
        rows.append(Download(
            user_id=user.id, url=item.url, video_id=item.video_id, title=item.title or item.url,
            uploader=item.uploader, thumbnail=item.thumbnail, duration=item.duration,
            preset_name=preset.name, options=preset.options, subfolder=subfolder,
            playlist_title=body.playlist_title, playlist_index=item.index if body.playlist_title else None,
            hidden=body.hidden or adult, age_limit=item.age_limit,
        ))
    db.add_all(rows)
    db.commit()
    for d in rows:
        await hub.publish("download", _out(d), user.id)
    manager.wake()
    return [_out(d) for d in rows]


@router.get("/downloads")
def list_downloads(
    request: Request,
    view: Literal["queue", "library", "all"] = "all",
    hidden: Literal["include", "exclude", "only"] = "include",
    q: str | None = None,
    playlist: str | None = None,
    standalone: bool = False,
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
    # Dashboards and scripts never see hidden videos.
    if api_key_from(request):
        hidden = "exclude"
    if hidden == "exclude":
        query = query.filter(Download.hidden.is_(False))
    elif hidden == "only":
        query = query.filter(Download.hidden.is_(True))
    if playlist is not None:
        query = query.filter(Download.playlist_title == playlist)
    elif standalone:
        query = query.filter(Download.playlist_title.is_(None))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Download.title.ilike(like), Download.uploader.ilike(like), Download.playlist_title.ilike(like)))

    total = query.count()
    order = {
        "queue": Download.created_at.asc(),
        "library": Download.finished_at.desc(),
        "all": Download.created_at.desc(),
    }[view]
    if playlist is not None:
        order = Download.playlist_index.asc()
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
    # Only media is shown in the browser. Anything else (e.g. an HTML or SVG file a
    # site served) is always a download, so it can never run script on this origin.
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if not media_type.startswith(("video/", "audio/", "image/")) or media_type == "image/svg+xml":
        inline, media_type = False, "application/octet-stream"
    return FileResponse(
        path, filename=path.name, media_type=media_type,
        content_disposition_type="inline" if inline else "attachment",
        headers={"Content-Security-Policy": "sandbox; default-src 'none'"},
    )




@router.get("/downloads/{download_id}")
def get_download(download_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """One download with everything, also of a hidden one ("tap to reveal")."""
    return serialize(_owned(db, user, download_id), manager.live(download_id), reveal=True)


@router.patch("/downloads/{download_id}")
async def set_hidden(download_id: int, body: HiddenBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = _owned(db, user, download_id)
    d.hidden = body.hidden
    db.commit()
    await hub.publish("download", _out(d), d.user_id)
    return _out(d)


async def _apply(db: Session, rows: list[Download], action: str, delete_files: bool) -> dict:
    """Deletes, hides or shows downloads; running ones are skipped when deleting."""
    done, skipped = [], 0
    for d in rows:
        if action == "delete":
            if d.status in ACTIVE or d.status == "queued":
                skipped += 1
                continue
            if delete_files:
                _delete_file(d)
            db.delete(d)
        else:
            d.hidden = action == "hide"
        done.append(d)
    db.commit()
    for d in done:
        if action == "delete":
            await hub.publish("download_removed", {"id": d.id}, d.user_id)
        else:
            await hub.publish("download", _out(d), d.user_id)
    return {"done": len(done), "skipped": skipped}


@router.post("/downloads/batch")
async def batch(body: BatchBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The same action for several downloads (selection in the library)."""
    query = db.query(Download).filter(Download.id.in_(set(body.ids)))
    if not user.is_admin:
        query = query.filter(Download.user_id == user.id)
    return await _apply(db, query.all(), body.action, body.delete_files)


@router.post("/downloads/cleanup")
async def cleanup(body: CleanupBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Deletes all finished single videos and/or playlists of the caller.
    With dry_run (the default) it only counts, for the second confirmation."""
    query = db.query(Download).filter(Download.user_id == user.id, Download.status.in_(FINISHED))
    if body.scope == "videos":
        query = query.filter(Download.playlist_title.is_(None))
    elif body.scope == "playlists":
        query = query.filter(Download.playlist_title.is_not(None))
    rows = query.all()
    summary = {
        "videos": sum(1 for d in rows if d.playlist_title is None),
        "playlists": len({d.playlist_title for d in rows if d.playlist_title is not None}),
        "playlist_videos": sum(1 for d in rows if d.playlist_title is not None),
        "bytes": sum(d.file_size or 0 for d in rows if d.status == "completed"),
    }
    if body.dry_run:
        return summary
    result = await _apply(db, rows, "delete", body.delete_files)
    return {**summary, "removed": result["done"]}


# -- ZIP of a selection ----------------------------------------------------------

_ZIP_TTL = 600
_zip_jobs: dict[str, tuple[int, float, list[int], list[str]]] = {}


@router.post("/zip")
def prepare_zip(body: ZipBody, user: User = Depends(current_user)):
    """Remembers a selection for a few minutes; the browser then downloads
    /api/zip/<token> like a normal file (no huge download through fetch)."""
    if not body.ids and not body.playlists:
        raise HTTPException(400, "Nichts ausgewählt")
    now = time.monotonic()
    for key in [k for k, job in _zip_jobs.items() if job[1] < now]:
        _zip_jobs.pop(key, None)
    token = secrets.token_urlsafe(16)
    _zip_jobs[token] = (user.id, now + _ZIP_TTL, body.ids, body.playlists)
    return {"url": f"/api/zip/{token}"}


@router.get("/zip/{token}")
def selection_zip(token: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = _zip_jobs.get(token)
    if job is None or job[0] != user.id or job[1] < time.monotonic():
        raise HTTPException(404, "Download-Link abgelaufen")
    _, _, ids, playlists = job
    files: list[tuple[Path, str]] = []
    seen: set[str] = set()
    rows = db.query(Download).filter(Download.id.in_(set(ids)), Download.status == "completed")
    if not user.is_admin:
        rows = rows.filter(Download.user_id == user.id)
    for d in rows.order_by(Download.finished_at.desc()).all():
        path = _resolve_file(d)
        if path is not None:
            name = path.name if path.name not in seen else f"{path.stem} ({d.id}){path.suffix}"
            seen.add(name)
            files.append((path, name))
    for title in playlists:
        folder = safe_component(title)
        files += [(path, f"{folder}/{name}") for path, name in _playlist_files(db, user, title)]
    if not files:
        raise HTTPException(404, "Keine fertigen Dateien in der Auswahl")
    name = f"{safe_component(playlists[0])}.zip" if len(playlists) == 1 and not ids else "Tubesy.zip"
    from urllib.parse import quote
    return StreamingResponse(
        _zip_stream(files),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


# -- playlists ---------------------------------------------------------------

@router.get("/playlists")
def list_playlists(q: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Completed downloads of the caller grouped by playlist."""
    query = db.query(
        Download.playlist_title,
        func.count(Download.id),
        func.coalesce(func.sum(Download.file_size), 0),
        func.max(Download.finished_at),
        func.min(Download.playlist_index),
    ).filter(
        Download.user_id == user.id, Download.status == "completed", Download.playlist_title.is_not(None),
        Download.hidden.is_(False),
    )
    if q:
        query = query.filter(Download.playlist_title.ilike(f"%{q.strip()}%"))
    groups = query.group_by(Download.playlist_title).order_by(func.max(Download.finished_at).desc()).all()

    out = []
    for title, count, size, finished, first_index in groups:
        first = (
            db.query(Download)
            .filter(
                Download.user_id == user.id, Download.status == "completed", Download.playlist_title == title,
                Download.hidden.is_(False),
            )
            .order_by(Download.playlist_index.asc())
            .first()
        )
        pending = db.query(func.count(Download.id)).filter(
            Download.user_id == user.id, Download.playlist_title == title, Download.status != "completed"
        ).scalar()
        out.append({
            "title": title,
            "count": count,
            "pending": pending or 0,
            "total_size": int(size or 0),
            "finished_at": finished.isoformat() if finished else None,
            "thumbnail": first.thumbnail if first else None,
            "uploader": first.uploader if first else None,
        })
    return out


def _playlist_files(db: Session, user: User, title: str) -> list[tuple[Path, str]]:
    rows = (
        db.query(Download)
        .filter(Download.user_id == user.id, Download.status == "completed", Download.playlist_title == title)
        .order_by(Download.playlist_index.asc())
        .all()
    )
    files, seen = [], set()
    for d in rows:
        path = _resolve_file(d)
        if path is None:
            continue
        name = path.name
        if name in seen:  # same video downloaded twice
            name = f"{path.stem} ({d.id}){path.suffix}"
        seen.add(name)
        files.append((path, name))
    return files


class _Cancelled(Exception):
    pass


class _QueueWriter:
    """File-like sink that hands written chunks to the response stream.
    zipfile detects that it cannot seek and writes a streaming-compatible archive."""

    def __init__(self, q: Queue, cancelled: Event):
        self.q = q
        self.cancelled = cancelled

    def write(self, data: bytes) -> int:
        if self.cancelled.is_set():
            raise _Cancelled
        if data:
            self.q.put(bytes(data))
        return len(data)

    def flush(self) -> None:
        pass


def _zip_stream(files: list[tuple[Path, str]]):
    q: Queue = Queue(maxsize=16)
    done = object()
    cancelled = Event()

    def produce():
        try:
            # Videos are already compressed: store them, which is fast and streams immediately.
            with zipfile.ZipFile(_QueueWriter(q, cancelled), "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
                for path, name in files:
                    with open(path, "rb") as src, zf.open(name, "w", force_zip64=True) as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)
        except _Cancelled:
            pass
        finally:
            if not cancelled.is_set():
                q.put(done)

    Thread(target=produce, daemon=True).start()
    try:
        while (chunk := q.get()) is not done:
            yield chunk
    finally:
        # Browser aborted the download: stop the producer and unblock it.
        cancelled.set()
        while not q.empty():
            q.get_nowait()


@router.get("/playlists/zip")
def playlist_zip(title: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    files = _playlist_files(db, user, title)
    if not files:
        raise HTTPException(404, "Keine fertigen Dateien in dieser Playlist")
    name = f"{safe_component(title)}.zip"
    from urllib.parse import quote
    return StreamingResponse(
        _zip_stream(files),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.delete("/playlists")
async def delete_playlist(title: str, delete_files: bool = True, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Download).filter(
        Download.user_id == user.id, Download.playlist_title == title, Download.status.not_in(ACTIVE)
    ).all()
    if not rows:
        raise HTTPException(404, "Playlist nicht gefunden")
    ids = []
    for d in rows:
        if delete_files:
            _delete_file(d)
        ids.append(d.id)
        db.delete(d)
    db.commit()
    for download_id in ids:
        await hub.publish("download_removed", {"id": download_id}, user.id)
    return {"removed": len(ids)}


@router.post("/playlists/batch")
async def playlists_batch(body: PlaylistBatchBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Deletes, hides or shows whole playlists of the caller."""
    rows = db.query(Download).filter(Download.user_id == user.id, Download.playlist_title.in_(set(body.titles))).all()
    return await _apply(db, rows, body.action, body.delete_files)


# -- supported sites -----------------------------------------------------------

@router.get("/extractors")
async def extractors(user: User = Depends(current_user)):
    return {"sites": await ytdlp.supported_sites()}
