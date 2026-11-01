from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_session
from ..deps import API_KEY_PREFIX
from ..models import ApiToken, Preset, UserSession
from ..security import hash_password, hash_token, new_token, verify_password
from ..services import notify
from ..services.downloads import used_bytes
from ..services.netcheck import ensure_allowed
from .auth import enforce_password_policy, user_out, validate_password

router = APIRouter(prefix="/api/account", tags=["account"])


class PasswordBody(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _p(cls, v: str) -> str:
        return validate_password(v)


class ProfileBody(BaseModel):
    email: str | None = None
    default_preset_id: int | None = None
    auto_hide_adult: bool | None = None
    cleanup_days: int | None = Field(None, ge=1, le=3650)
    clear_cleanup_days: bool = False


class NotifyBody(BaseModel):
    ntfy_url: str = Field("", max_length=500)
    ntfy_token: str | None = Field(None, max_length=500)  # None = keep, "" = remove
    telegram_token: str | None = Field(None, max_length=200)
    telegram_chat: str = Field("", max_length=100)
    on_done: bool = True
    on_failed: bool = True

    @field_validator("ntfy_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("Bitte eine gültige http(s)-URL angeben")
        return v


@router.get("")
def overview(sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    user = sess.user
    return {**user_out(user), "used_bytes": used_bytes(db, user.id)}


@router.patch("")
def update_profile(body: ProfileBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    user = sess.user
    if body.default_preset_id is not None:
        preset = db.get(Preset, body.default_preset_id)
        if preset is None or preset.user_id not in (None, user.id):
            raise HTTPException(404, "Preset nicht gefunden")
    user.email = (body.email or "").strip() or None
    user.default_preset_id = body.default_preset_id
    if body.auto_hide_adult is not None:
        user.auto_hide_adult = body.auto_hide_adult
    if body.clear_cleanup_days:
        user.cleanup_days = None
    elif body.cleanup_days is not None:
        user.cleanup_days = body.cleanup_days
    db.commit()
    return user_out(user)


@router.post("/password")
def change_password(body: PasswordBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    user = sess.user
    if not verify_password(user.password_hash, body.current_password):
        raise HTTPException(400, "Aktuelles Passwort ist falsch")
    enforce_password_policy(db, body.new_password, user.role)
    user.password_hash = hash_password(body.new_password)
    # Signing out everywhere else is what people expect after a password change.
    db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.id != sess.id).delete()
    db.commit()
    return {"ok": True}


@router.get("/sessions")
def sessions(sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    rows = db.query(UserSession).filter_by(user_id=sess.user_id).order_by(UserSession.last_seen_at.desc()).all()
    return [
        {
            "id": s.id, "ip": s.ip, "user_agent": s.user_agent, "current": s.id == sess.id,
            "created_at": s.created_at.isoformat(), "last_seen_at": s.last_seen_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
        }
        for s in rows
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    target = db.get(UserSession, session_id)
    if target is None or target.user_id != sess.user_id:
        raise HTTPException(404, "Sitzung nicht gefunden")
    db.delete(target)
    db.commit()
    return {"ok": True}


class TokenBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scope: Literal["read", "full"] = "read"


def _token_out(t: ApiToken) -> dict:
    return {
        "id": t.id, "name": t.name, "prefix": t.prefix, "scope": t.scope,
        "created_at": t.created_at.isoformat(),
        "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
    }


@router.get("/tokens")
def tokens(sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    rows = db.query(ApiToken).filter_by(user_id=sess.user_id).order_by(ApiToken.created_at.desc()).all()
    return [_token_out(t) for t in rows]


@router.post("/tokens")
def create_token(body: TokenBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    if db.query(ApiToken).filter_by(user_id=sess.user_id).count() >= 20:
        raise HTTPException(409, "Höchstens 20 API-Schlüssel pro Konto")
    key = API_KEY_PREFIX + new_token()
    t = ApiToken(user_id=sess.user_id, name=body.name.strip(), scope=body.scope,
                 token_hash=hash_token(key), prefix=key[:10])
    db.add(t)
    db.commit()
    # Only the hash is stored, so the key can be shown exactly once.
    return {**_token_out(t), "key": key}


@router.delete("/tokens/{token_id}")
def delete_token(token_id: int, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    t = db.get(ApiToken, token_id)
    if t is None or t.user_id != sess.user_id:
        raise HTTPException(404, "API-Schlüssel nicht gefunden")
    db.delete(t)
    db.commit()
    return {"ok": True}


# -- notifications -------------------------------------------------------------

@router.get("/notifications")
def get_notifications(sess: UserSession = Depends(current_session)):
    return notify.public(sess.user)


@router.put("/notifications")
async def put_notifications(body: NotifyBody, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    user = sess.user
    if body.ntfy_url:
        await ensure_allowed(db, user, [body.ntfy_url])
    cfg = notify.config_of(user)
    cfg.update(ntfy_url=body.ntfy_url, telegram_chat=body.telegram_chat.strip(), on_done=body.on_done, on_failed=body.on_failed)
    for key in notify.SECRETS:
        value = getattr(body, key)
        if value is not None:
            cfg[key] = value.strip()
    user.notify = cfg
    db.commit()
    return notify.public(user)


@router.post("/notifications/test")
async def test_notifications(sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    cfg = notify.config_of(sess.user)
    if not (cfg["ntfy_url"] or (cfg["telegram_token"] and cfg["telegram_chat"])):
        raise HTTPException(400, "Noch kein Dienst eingerichtet")
    errors = await notify.send(cfg, "Tubesy", notify.test_text(db))
    if errors:
        raise HTTPException(502, " · ".join(errors))
    return {"ok": True}

