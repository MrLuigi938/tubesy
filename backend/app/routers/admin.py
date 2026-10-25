import platform
import shutil
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..deps import require_admin
from ..models import Download, Invite, User, UserSession
from ..security import hash_password, hash_token, new_token
from ..services import settings as app_settings
from ..services import ytdlp
from ..services.downloads import download_dir_writable, manager, user_root
from ..services.events import hub
from ..services.updates import checker
from .auth import enforce_password_policy, user_out, validate_password, validate_username

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

GB = 1024**3


class CreateUserBody(BaseModel):
    username: str
    password: str
    email: str | None = None
    role: Literal["admin", "user"] = "user"
    quota_gb: float | None = Field(None, ge=0)

    @field_validator("username")
    @classmethod
    def _u(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def _p(cls, v: str) -> str:
        return validate_password(v)


class UpdateUserBody(BaseModel):
    email: str | None = None
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None
    quota_gb: float | None = Field(None, ge=0)
    clear_quota: bool = False
    password: str | None = None

    @field_validator("password")
    @classmethod
    def _p(cls, v: str | None) -> str | None:
        return validate_password(v) if v else None


class InviteBody(BaseModel):
    note: str | None = Field(None, max_length=255)
    role: Literal["admin", "user"] = "user"
    max_uses: int = Field(1, ge=1, le=1000)
    expires_days: int | None = Field(7, ge=1, le=365)


class SettingsBody(BaseModel):
    registration_mode: Literal["closed", "invite", "open"] | None = None
    max_concurrent_downloads: int | None = Field(None, ge=1, le=20)
    max_concurrent_per_user: int | None = Field(None, ge=1, le=20)
    default_quota_gb: float | None = Field(None, ge=0)
    clear_default_quota: bool = False
    session_days: int | None = Field(None, ge=1, le=365)
    max_playlist_items: int | None = Field(None, ge=1, le=5000)
    min_password_length: int | None = Field(None, ge=6, le=64)
    update_check: bool | None = None


def _stats(db: Session) -> dict[int, dict]:
    rows = (
        db.query(
            Download.user_id,
            func.count(Download.id),
            func.coalesce(func.sum(Download.file_size), 0),
        )
        .filter(Download.status == "completed")
        .group_by(Download.user_id)
        .all()
    )
    return {uid: {"downloads": n, "used_bytes": int(size)} for uid, n, size in rows}


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()


# -- users -------------------------------------------------------------------

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    stats = _stats(db)
    return [
        {**user_out(u), **stats.get(u.id, {"downloads": 0, "used_bytes": 0})}
        for u in db.query(User).order_by(User.username).all()
    ]


@router.post("/users")
def create_user(body: CreateUserBody, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=body.username).count():
        raise HTTPException(409, "Benutzername ist bereits vergeben")
    enforce_password_policy(db, body.password, body.role)
    user = User(
        username=body.username, email=(body.email or "").strip() or None, role=body.role,
        password_hash=hash_password(body.password),
        quota_bytes=int(body.quota_gb * GB) if body.quota_gb else None,
    )
    db.add(user)
    db.commit()
    return user_out(user)


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UpdateUserBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    demoting = (body.role == "user" and user.role == "admin") or (body.is_active is False and user.role == "admin")
    if demoting and _admin_count(db) <= 1:
        raise HTTPException(409, "Der letzte Administrator kann nicht herabgestuft oder deaktiviert werden")

    if body.email is not None:
        user.email = body.email.strip() or None
    if body.role is not None:
        user.role = body.role
    if body.clear_quota:
        user.quota_bytes = None
    elif body.quota_gb is not None:
        user.quota_bytes = int(body.quota_gb * GB)
    revoke = False
    if body.is_active is not None:
        user.is_active = body.is_active
        revoke = not body.is_active
    if body.password:
        enforce_password_policy(db, body.password, user.role)
        user.password_hash = hash_password(body.password)
        revoke = True
    if revoke and user.id != admin.id:
        db.query(UserSession).filter_by(user_id=user.id).delete()
        hub.disconnect_user(user.id)
    db.commit()
    return user_out(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, delete_files: bool = False, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Benutzer nicht gefunden")
    if user.id == admin.id:
        raise HTTPException(409, "Das eigene Konto kann nicht gelöscht werden")
    manager.cancel_user(user.id, db)
    hub.disconnect_user(user.id)
    if delete_files:
        root = user_root(user).resolve()
        if root.is_relative_to(config.DOWNLOAD_DIR) and root != config.DOWNLOAD_DIR:
            shutil.rmtree(root, ignore_errors=True)
    db.delete(user)
    db.commit()
    return {"ok": True}


# -- invites -----------------------------------------------------------------

def _invite_out(inv: Invite) -> dict:
    return {
        "id": inv.id, "note": inv.note, "role": inv.role, "max_uses": inv.max_uses, "uses": inv.uses,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "created_at": inv.created_at.isoformat(),
    }


@router.get("/invites")
def list_invites(db: Session = Depends(get_db)):
    return [_invite_out(i) for i in db.query(Invite).order_by(Invite.created_at.desc()).all()]


@router.post("/invites")
def create_invite(body: InviteBody, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    token = new_token()
    inv = Invite(
        token_hash=hash_token(token), note=body.note, role=body.role, max_uses=body.max_uses, created_by=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_days) if body.expires_days else None,
    )
    db.add(inv)
    db.commit()
    # The token is only stored hashed, so this is the only time it can be shown.
    return {**_invite_out(inv), "token": token}


@router.delete("/invites/{invite_id}")
def delete_invite(invite_id: int, db: Session = Depends(get_db)):
    inv = db.get(Invite, invite_id)
    if inv is None:
        raise HTTPException(404, "Einladung nicht gefunden")
    db.delete(inv)
    db.commit()
    return {"ok": True}


# -- settings & system -------------------------------------------------------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return app_settings.get_all(db)


@router.put("/settings")
async def put_settings(body: SettingsBody, db: Session = Depends(get_db)):
    values = body.model_dump(exclude_none=True, exclude={"clear_default_quota"})
    if body.clear_default_quota:
        values["default_quota_gb"] = None
    result = app_settings.update(db, values)
    manager.wake()  # concurrency limits may have been raised
    if "update_check" in values:
        checker.check_soon()  # show or hide the hint right away
    return result


@router.get("/system")
async def system(db: Session = Depends(get_db)):
    disk = shutil.disk_usage(config.DOWNLOAD_DIR)
    counts = dict(db.query(Download.status, func.count(Download.id)).group_by(Download.status).all())
    users = db.query(User).count()
    db.close()
    return {
        "version": config.VERSION,
        "update": checker.update,
        "update_checked_at": checker.checked_at.isoformat() if checker.checked_at else None,
        "python": platform.python_version(),
        "ytdlp_version": await ytdlp.version(),
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "deno": shutil.which("deno") is not None,
        "download_dir": str(config.DOWNLOAD_DIR),
        "download_dir_writable": download_dir_writable(),
        "disk_total": disk.total,
        "disk_free": disk.free,
        "users": users,
        "downloads_by_status": counts,
    }


@router.post("/ytdlp/update")
async def update_ytdlp():
    try:
        return {"ytdlp_version": await ytdlp.self_update()}
    except RuntimeError as exc:
        raise HTTPException(500, f"Update fehlgeschlagen: {exc}")
