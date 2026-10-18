import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import client_ip, current_session, current_user
from ..models import Invite, User, UserSession
from ..security import (
    hash_password, hash_token, login_ip_limiter, login_user_limiter, needs_rehash, new_token,
    register_limiter, verify_password,
)
from ..services import settings as app_settings

router = APIRouter(prefix="/api", tags=["auth"])

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
RESERVED = {"con", "nul", "prn", "aux"}  # Windows device names break SMB shares


def validate_username(v: str) -> str:
    v = v.strip().lower()
    if not USERNAME_RE.fullmatch(v) or v in RESERVED:
        raise ValueError("3–32 Zeichen: Kleinbuchstaben, Ziffern, . _ -")
    return v


MIN_PASSWORD_LENGTH = 6


def validate_password(v: str) -> str:
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Mindestens {MIN_PASSWORD_LENGTH} Zeichen")
    if len(v) > 256:
        raise ValueError("Höchstens 256 Zeichen")
    return v


def required_length(db: Session, role: str) -> int:
    if role == "admin":
        return MIN_PASSWORD_LENGTH
    return max(MIN_PASSWORD_LENGTH, int(app_settings.get(db, "min_password_length")))


def enforce_password_policy(db: Session, password: str, role: str) -> None:
    """The admin-configurable minimum applies to normal users only."""
    need = required_length(db, role)
    if len(password) < need:
        raise HTTPException(400, f"Das Passwort muss mindestens {need} Zeichen haben")


class Credentials(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def _u(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def _p(cls, v: str) -> str:
        return validate_password(v)


class LoginBody(BaseModel):
    username: str
    password: str
    remember: bool = True


class RegisterBody(Credentials):
    email: str | None = None
    invite: str | None = None


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "quota_bytes": user.quota_bytes,
        "default_preset_id": user.default_preset_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def start_session(db: Session, request: Request, response: Response, user: User, remember: bool = True) -> None:
    token = new_token()
    days = int(app_settings.get(db, "session_days"))
    now = datetime.now(timezone.utc)
    db.add(UserSession(
        token_hash=hash_token(token), user_id=user.id, expires_at=now + timedelta(days=days if remember else 1),
        ip=client_ip(request), user_agent=(request.headers.get("user-agent") or "")[:512],
    ))
    user.last_login_at = now
    db.commit()
    secure = config.COOKIE_SECURE == "true" or (config.COOKIE_SECURE == "auto" and request.url.scheme == "https")
    response.set_cookie(
        config.SESSION_COOKIE, token, httponly=True, samesite="lax", secure=secure, path="/",
        max_age=days * 86400 if remember else None,
    )


def _valid_invite(db: Session, token: str | None) -> Invite | None:
    if not token:
        return None
    inv = db.query(Invite).filter_by(token_hash=hash_token(token)).one_or_none()
    if inv is None or inv.uses >= inv.max_uses:
        return None
    if inv.expires_at:
        expires = inv.expires_at if inv.expires_at.tzinfo else inv.expires_at.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return None
    return inv


@router.get("/status")
def status(db: Session = Depends(get_db), invite: str | None = None):
    return {
        "needs_setup": db.query(User).count() == 0,
        "registration_mode": app_settings.get(db, "registration_mode"),
        "invite_valid": _valid_invite(db, invite) is not None if invite else None,
        "min_password_length": required_length(db, "user"),
        "min_password_length_admin": MIN_PASSWORD_LENGTH,
    }


@router.post("/setup")
def setup(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(409, "Die Einrichtung wurde bereits abgeschlossen")
    user = User(username=body.username, password_hash=hash_password(body.password), role="admin")
    db.add(user)
    db.commit()
    start_session(db, request, response, user)
    return user_out(user)


@router.post("/auth/login")
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    username = body.username.strip().lower()
    wait = max(login_ip_limiter.blocked(ip), login_user_limiter.blocked(username))
    if wait:
        raise HTTPException(429, f"Zu viele Anmeldeversuche. Bitte in {wait // 60 + 1} Minuten erneut versuchen.")

    user = db.query(User).filter_by(username=username).one_or_none()
    if not verify_password(user.password_hash if user else None, body.password) or not user.is_active:
        login_ip_limiter.hit(ip)
        login_user_limiter.hit(username)
        raise HTTPException(401, "Benutzername oder Passwort falsch")

    login_user_limiter.reset(username)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    start_session(db, request, response, user, body.remember)
    return user_out(user)


@router.post("/auth/logout")
def logout(response: Response, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(db.merge(sess))
    db.commit()
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.post("/auth/register")
def register(body: RegisterBody, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if register_limiter.blocked(ip):
        raise HTTPException(429, "Zu viele Registrierungen von dieser Adresse")

    mode = app_settings.get(db, "registration_mode")
    invite = _valid_invite(db, body.invite)
    if body.invite and invite is None:
        raise HTTPException(400, "Die Einladung ist ungültig oder abgelaufen")
    if invite is None and mode != "open":
        raise HTTPException(403, "Registrierung nur mit Einladung möglich" if mode == "invite" else "Registrierung ist deaktiviert")
    if db.query(User).filter_by(username=body.username).count():
        raise HTTPException(409, "Benutzername ist bereits vergeben")

    enforce_password_policy(db, body.password, invite.role if invite else "user")
    register_limiter.hit(ip)
    quota_gb = app_settings.get(db, "default_quota_gb")
    user = User(
        username=body.username,
        email=(body.email or "").strip() or None,
        password_hash=hash_password(body.password),
        role=invite.role if invite else "user",
        quota_bytes=int(float(quota_gb) * 1024**3) if quota_gb else None,
    )
    db.add(user)
    if invite:
        invite.uses += 1
    db.commit()
    start_session(db, request, response, user)
    return user_out(user)
