"""Channel and playlist subscriptions of the signed-in user (browser only)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_session
from ..models import Download, Preset, Subscription, UserSession
from ..services import settings as app_settings
from ..services import subscriptions, ytdlp
from ..services.netcheck import ensure_allowed
from .downloads import _check_url

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

INTERVALS = (1, 3, 6, 12, 24, 72, 168)


class CreateBody(BaseModel):
    url: str
    preset_id: int | None = None
    own_folder: bool = True
    hidden: bool = False
    interval_hours: int = 6
    backfill: int = Field(0, ge=0, le=50)

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return ytdlp.normalize_url(_check_url(v))

    @field_validator("interval_hours")
    @classmethod
    def _interval(cls, v: int) -> int:
        if v not in INTERVALS:
            raise ValueError("Ungültiger Abstand")
        return v


class UpdateBody(BaseModel):
    preset_id: int | None = None
    own_folder: bool | None = None
    hidden: bool | None = None
    interval_hours: int | None = None
    enabled: bool | None = None

    @field_validator("interval_hours")
    @classmethod
    def _interval(cls, v: int | None) -> int | None:
        if v is not None and v not in INTERVALS:
            raise ValueError("Ungültiger Abstand")
        return v


def _out(db: Session, sub: Subscription) -> dict:
    count = db.query(func.count(Download.id)).filter(Download.subscription_id == sub.id).scalar()
    preset = db.get(Preset, sub.preset_id) if sub.preset_id else None
    return {
        "id": sub.id, "url": sub.url, "title": sub.title, "thumbnail": sub.thumbnail,
        "preset_id": sub.preset_id, "preset_name": preset.name if preset else None,
        "own_folder": sub.own_folder, "hidden": sub.hidden, "interval_hours": sub.interval_hours,
        "enabled": sub.enabled, "downloads": count or 0, "last_error": sub.last_error,
        "last_checked_at": sub.last_checked_at.isoformat() if sub.last_checked_at else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


def _own(db: Session, sess: UserSession, sub_id: int) -> Subscription:
    sub = db.get(Subscription, sub_id)
    if sub is None or sub.user_id != sess.user_id:
        raise HTTPException(404, "Abo nicht gefunden")
    return sub


def _check_preset(db: Session, sess: UserSession, preset_id: int | None) -> None:
    if preset_id is not None:
        preset = db.get(Preset, preset_id)
        if preset is None or preset.user_id not in (None, sess.user_id):
            raise HTTPException(404, "Preset nicht gefunden")


@router.get("")
def list_subscriptions(sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    rows = db.query(Subscription).filter_by(user_id=sess.user_id).order_by(Subscription.created_at.desc()).all()
    return [_out(db, s) for s in rows]


@router.post("")
async def create(body: CreateBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    await ensure_allowed(db, sess.user, [body.url])
    _check_preset(db, sess, body.preset_id)
    if db.query(Subscription).filter_by(user_id=sess.user_id, url=body.url).count():
        raise HTTPException(409, "Dieses Abo gibt es schon")
    max_items = min(subscriptions.CHECK_LIMIT, int(app_settings.get(db, "max_playlist_items")))
    user_id = sess.user_id
    db.close()  # yt-dlp can take a while
    try:
        info = await ytdlp.probe(body.url, max_items)
    except ytdlp.ProbeError as exc:
        raise HTTPException(422, str(exc))
    if info["type"] != "playlist":
        raise HTTPException(422, subscriptions.NOT_A_LIST)

    from ..database import SessionLocal

    with SessionLocal() as s:
        thumb = info.get("thumbnail") or next((e.get("thumbnail") for e in info["entries"] if e.get("thumbnail")), None)
        sub = Subscription(
            user_id=user_id, url=body.url, title=info.get("title") or body.url, thumbnail=thumb,
            preset_id=body.preset_id, own_folder=body.own_folder, hidden=body.hidden, interval_hours=body.interval_hours,
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    # The first check only remembers what is there already – plus the newest N if wanted.
    queued = await subscriptions.check(sub_id, backfill=body.backfill)
    with SessionLocal() as s:
        return {**_out(s, s.get(Subscription, sub_id)), "queued": queued}


@router.patch("/{sub_id}")
def update(sub_id: int, body: UpdateBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    sub = _own(db, sess, sub_id)
    _check_preset(db, sess, body.preset_id)
    for field in ("own_folder", "hidden", "interval_hours", "enabled"):
        value = getattr(body, field)
        if value is not None:
            setattr(sub, field, value)
    if "preset_id" in body.model_fields_set:
        sub.preset_id = body.preset_id
    db.commit()
    return _out(db, sub)


@router.delete("/{sub_id}")
def delete(sub_id: int, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    """Ends the subscription; downloaded videos stay in the library."""
    db.delete(_own(db, sess, sub_id))
    db.commit()
    return {"ok": True}


@router.post("/{sub_id}/check")
async def check_now(sub_id: int, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    _own(db, sess, sub_id)
    db.close()
    queued = await subscriptions.check(sub_id)
    from ..database import SessionLocal

    with SessionLocal() as s:
        return {**_out(s, s.get(Subscription, sub_id)), "queued": queued}
