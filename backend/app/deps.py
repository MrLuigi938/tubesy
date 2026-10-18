from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .models import User, UserSession
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


def current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    sess = resolve_session(db, request.cookies.get(config.SESSION_COOKIE))
    if sess is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    return sess


def current_user(sess: UserSession = Depends(current_session)) -> User:
    return sess.user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nur für Administratoren")
    return user
