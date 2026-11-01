"""Clean-up rules (run hourly by the scheduler).

- per user: finished downloads older than *cleanup_days* are deleted with their files
- per instance: below *cleanup_min_free_gb* free space, the oldest finished
  downloads of all users are deleted until there is enough room again
Running and waiting downloads are never touched.
"""
import logging
import shutil
from datetime import datetime, timedelta, timezone

from .. import config
from ..database import SessionLocal
from ..models import Download, User
from . import settings as app_settings
from .downloads import FINISHED, delete_file
from .events import hub

log = logging.getLogger("tubesy.cleanup")
GB = 1024**3


def _remove(db, rows: list[Download]) -> list[tuple[int, int]]:
    removed = []
    for d in rows:
        delete_file(d)
        removed.append((d.id, d.user_id))
        db.delete(d)
    return removed


async def run_rules() -> int:
    """Applies both rules; returns how many downloads were deleted."""
    removed: list[tuple[int, int]] = []
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for user in db.query(User).filter(User.cleanup_days.is_not(None), User.cleanup_days > 0):
            old = (
                db.query(Download)
                .filter(Download.user_id == user.id, Download.status.in_(FINISHED),
                        Download.finished_at < now - timedelta(days=user.cleanup_days))
                .all()
            )
            if old:
                log.info("Aufräumen: %d Downloads von %s älter als %d Tage", len(old), user.username, user.cleanup_days)
                removed += _remove(db, old)
        db.commit()

        min_free = app_settings.get(db, "cleanup_min_free_gb")
        if min_free:
            target = float(min_free) * GB
            free = shutil.disk_usage(config.DOWNLOAD_DIR).free
            if free < target:
                oldest = (
                    db.query(Download)
                    .filter(Download.status == "completed", Download.file_size.is_not(None))
                    .order_by(Download.finished_at.asc())
                )
                batch = []
                for d in oldest:
                    if free >= target:
                        break
                    batch.append(d)
                    free += d.file_size or 0
                if batch:
                    log.info("Aufräumen: wenig Speicher, %d älteste Downloads gelöscht", len(batch))
                    removed += _remove(db, batch)
                db.commit()
    for download_id, user_id in removed:
        await hub.publish("download_removed", {"id": download_id}, user_id)
    return len(removed)
