from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import ApiToken, User, UserSession
from .security import hash_token

_TOUCH_INTERVAL = timedelta(minutes=5)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _as_aware(value: datetime) -> datetime:
    # SQLite drops tzinfo; everything is stored as UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def resolve_session(db: Session, token: str | None) -> UserSession | None:
    if not token:
        return None
    sess = db.query(UserSession).filter_by(token_hash=hash_token(token)).one_or_none()
    if sess is None:
        return None
    now = datetime.now(timezone.utc)
    if _as_aware(sess.expires_at) < now or not sess.user.is_active:
        db.delete(sess)
        db.commit()
        return None
    if now - _as_aware(sess.last_seen_at) > _TOUCH_INTERVAL:
        sess.last_seen_at = now
        db.commit()
    return sess


API_KEY_PREFIX = "tsy_"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def api_key_from(request: Request) -> str | None:
    """Reads an API key from X-Api-Key or 'Authorization: Bearer'."""
    key = request.headers.get("x-api-key")
    if not key:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:]
    return key.strip() if key else None


def current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    # Account and session management is only possible with a browser login.
    if api_key_from(request):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mit einem API-Schlüssel nicht möglich")
    sess = resolve_session(db, request.cookies.get(config.SESSION_COOKIE))
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    return sess


def _token_user(request: Request, db: Session, key: str) -> User:
    token = db.query(ApiToken).filter_by(token_hash=hash_token(key)).one_or_none()
    if token is None or not token.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ungültiger API-Schlüssel")
    if token.scope == "read" and request.method not in SAFE_METHODS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dieser API-Schlüssel darf nur lesen")
    now = datetime.now(timezone.utc)
    if token.last_used_at is None or now - _as_aware(token.last_used_at) > _TOUCH_INTERVAL:
        token.last_used_at = now
        db.commit()
    return token.user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Browser session cookie or API key. With a key present, the cookie is ignored."""
    key = api_key_from(request)
    if key:
        return _token_user(request, db, key)
    sess = resolve_session(db, request.cookies.get(config.SESSION_COOKIE))
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    return sess.user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nur für Administratoren")
    return user
