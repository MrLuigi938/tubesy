from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_session
from ..deps import API_KEY_PREFIX
from ..models import ApiToken, Preset, UserSession
from ..security import hash_password, hash_token, new_token, verify_password
from ..services.downloads import used_bytes
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
