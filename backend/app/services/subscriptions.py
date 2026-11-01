"""Channel and playlist subscriptions: new videos are queued on their own.

Each check lists the newest entries with yt-dlp and queues the ones the
subscription has not seen yet. Seen videos are remembered, so a deleted
download is never fetched again.
"""
import logging
from datetime import datetime, timedelta, timezone

from ..database import SessionLocal
from ..models import Download, Preset, Subscription, SubscriptionSeen
from . import settings as app_settings
from . import ytdlp
from .downloads import ADULT_AGE, manager, safe_component, serialize
from .events import hub
from .netcheck import LOCAL_NOT_ALLOWED, is_local

log = logging.getLogger("tubesy.subscriptions")

# How many of the newest entries a check looks at.
CHECK_LIMIT = 50
NOT_A_LIST = "Kein Kanal und keine Playlist"
NO_PRESET = "Kein Preset gefunden"


def entry_key(entry: dict) -> str:
    return (entry.get("video_id") or entry["url"])[:512]


def preset_for(db, sub: Subscription) -> Preset | None:
    """The subscription's preset, else the user's default, else the first global one."""
    for preset_id in (sub.preset_id, sub.user.default_preset_id):
        preset = db.get(Preset, preset_id) if preset_id else None
        if preset is not None and preset.user_id in (None, sub.user_id):
            return preset
    return db.query(Preset).filter(Preset.user_id.is_(None)).order_by(Preset.id).first()


def is_due(sub: Subscription, now: datetime) -> bool:
    if not sub.enabled:
        return False
    if sub.last_checked_at is None:
        return True
    last = sub.last_checked_at if sub.last_checked_at.tzinfo else sub.last_checked_at.replace(tzinfo=timezone.utc)
    return now - last >= timedelta(hours=sub.interval_hours)


def _fail(sub_id: int, message: str) -> None:
    with SessionLocal() as db:
        sub = db.get(Subscription, sub_id)
        if sub is not None:
            sub.last_checked_at = datetime.now(timezone.utc)
            sub.last_error = message[:2000]
            db.commit()


async def check(sub_id: int, backfill: int | None = None) -> int:
    """Queues the new videos of a subscription and returns how many.

    backfill is for the first check: the first N entries of the list (on a
    channel the newest videos) are queued, all others only marked as known."""
    with SessionLocal() as db:
        sub = db.get(Subscription, sub_id)
        if sub is None:
            return 0
        url, user_id = sub.url, sub.user_id
        local_blocked = not sub.user.is_admin and not app_settings.get(db, "allow_local_urls")
        limit = min(CHECK_LIMIT, int(app_settings.get(db, "max_playlist_items")))
    if local_blocked and await is_local(url):
        _fail(sub_id, LOCAL_NOT_ALLOWED)
        return 0
    try:
        info = await ytdlp.probe(url, limit)
    except ytdlp.ProbeError as exc:
        _fail(sub_id, str(exc))
        return 0
    if info["type"] != "playlist":
        _fail(sub_id, NOT_A_LIST)
        return 0

    with SessionLocal() as db:
        sub = db.get(Subscription, sub_id)
        if sub is None:
            return 0
        seen = {key for (key,) in db.query(SubscriptionSeen.key).filter_by(subscription_id=sub.id)}
        new: list[dict] = []
        for entry in info["entries"]:
            key = entry_key(entry)
            if key not in seen:
                seen.add(key)
                new.append(entry)
                db.add(SubscriptionSeen(subscription_id=sub.id, key=key))
        queue = new if backfill is None else new[:backfill]
        preset = preset_for(db, sub)
        sub.last_checked_at = datetime.now(timezone.utc)
        sub.last_error = None if preset is not None or not queue else NO_PRESET
        rows = []
        if preset is not None:
            folder = safe_component(sub.title) if sub.own_folder else None
            # Lists start with the newest video; queue the older ones first.
            for entry in reversed(queue):
                age = entry.get("age_limit")
                rows.append(Download(
                    user_id=sub.user_id, url=entry["url"], video_id=entry.get("video_id"),
                    title=entry.get("title") or entry["url"], uploader=entry.get("uploader"),
                    thumbnail=entry.get("thumbnail"), duration=entry.get("duration"),
                    preset_name=preset.name, options=preset.options, subscription_id=sub.id,
                    subfolder=folder, playlist_title=sub.title if sub.own_folder else None,
                    hidden=sub.hidden or ((age or 0) >= ADULT_AGE and sub.user.auto_hide_adult), age_limit=age,
                ))
            db.add_all(rows)
        db.commit()
        out = [serialize(d) for d in rows]
    for data in out:
        await hub.publish("download", data, user_id)
    if out:
        manager.wake()
        log.info("Abo %s: %d neue Videos eingereiht", sub_id, len(out))
    return len(out)


async def check_due() -> None:
    """Checks every subscription whose interval has passed (called by the scheduler)."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        due = [s.id for s in db.query(Subscription).filter(Subscription.enabled.is_(True)) if is_due(s, now)]
    for sub_id in due:
        try:
            await check(sub_id)
        except Exception:
            log.exception("Abo %s: Prüfung fehlgeschlagen", sub_id)
