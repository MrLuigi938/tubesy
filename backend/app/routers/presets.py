from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Preset, User
from ..services.ytdlp import SPONSORBLOCK_CATEGORIES, PresetOptions

router = APIRouter(prefix="/api/presets", tags=["presets"])


class PresetBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    options: PresetOptions
    is_global: bool = False


def out(p: Preset) -> dict:
    return {"id": p.id, "name": p.name, "options": p.options, "is_global": p.user_id is None}


def _editable(db: Session, user: User, preset_id: int) -> Preset:
    p = db.get(Preset, preset_id)
    if p is None or p.user_id not in (None, user.id):
        raise HTTPException(404, "Preset nicht gefunden")
    if p.user_id is None and not user.is_admin:
        raise HTTPException(403, "Globale Presets können nur Administratoren ändern")
    return p


@router.get("")
def list_presets(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Preset)
        .filter(or_(Preset.user_id.is_(None), Preset.user_id == user.id))
        .order_by(Preset.user_id.is_not(None), Preset.id)
        .all()
    )
    return {
        "items": [out(p) for p in rows],
        "defaults": PresetOptions().model_dump(),
        "sponsorblock_categories": sorted(SPONSORBLOCK_CATEGORIES),
    }


@router.post("")
def create(body: PresetBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.is_global and not user.is_admin:
        raise HTTPException(403, "Globale Presets können nur Administratoren anlegen")
    p = Preset(user_id=None if body.is_global else user.id, name=body.name.strip(), options=body.options.model_dump())
    db.add(p)
    db.commit()
    return out(p)


@router.put("/{preset_id}")
def update(preset_id: int, body: PresetBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _editable(db, user, preset_id)
    p.name, p.options = body.name.strip(), body.options.model_dump()
    db.commit()
    return out(p)


@router.delete("/{preset_id}")
def delete(preset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _editable(db, user, preset_id)
    if p.user_id is None and db.query(Preset).filter(Preset.user_id.is_(None)).count() <= 1:
        raise HTTPException(409, "Mindestens ein globales Preset muss bestehen bleiben")
    db.query(User).filter(User.default_preset_id == p.id).update({"default_preset_id": None})
    db.delete(p)
    db.commit()
    return {"ok": True}
