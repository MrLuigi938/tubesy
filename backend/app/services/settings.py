"""Admin-editable application settings stored in the database."""
from sqlalchemy.orm import Session

from ..models import Setting

DEFAULTS: dict[str, object] = {
    "registration_mode": "invite",  # closed | invite | open
    "max_concurrent_downloads": 3,
    "max_concurrent_per_user": 2,
    "default_quota_gb": None,  # applied to newly registered users
    "session_days": 30,
    "max_playlist_items": 500,
    # Minimum length for normal users; admins only need MIN_PASSWORD_LENGTH.
    "min_password_length": 6,
    # Ask GitHub twice a day for a newer Tubesy release (only a hint, nothing is installed).
    "update_check": True,
    # Language picked during setup (de | en); names the built-in presets.
    "language": "de",
}


def get_all(db: Session) -> dict[str, object]:
    values = dict(DEFAULTS)
    for row in db.query(Setting).all():
        if row.key in DEFAULTS:
            values[row.key] = row.value
    return values


def get(db: Session, key: str):
    row = db.get(Setting, key)
    return row.value if row is not None else DEFAULTS[key]


def update(db: Session, values: dict[str, object]) -> dict[str, object]:
    for key, value in values.items():
        if key not in DEFAULTS:
            continue
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return get_all(db)
