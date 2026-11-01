"""Messages when downloads are finished: ntfy and Telegram, set up per user.

A single video is reported on its own; for a playlist (or a subscription folder)
one message comes when its last download is through. Hidden videos are never
named. Browser notifications are shown by the web interface itself.
"""
import asyncio
import json
import logging
import urllib.parse
import urllib.request
from datetime import timedelta, timezone

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Download, User
from . import settings as app_settings

log = logging.getLogger("tubesy.notify")

TEXTS = {
    "de": {
        "done": "Fertig: {title}",
        "failed": "Fehlgeschlagen: {title}",
        "hidden": "ein ausgeblendetes Video",
        "playlist": "Playlist „{title}“: {done} fertig",
        "playlist_failed": ", {failed} fehlgeschlagen",
        "hidden_playlist": "eine ausgeblendete Playlist",
        "test": "Tubesy sagt Hallo – Benachrichtigungen funktionieren.",
    },
    "en": {
        "done": "Done: {title}",
        "failed": "Failed: {title}",
        "hidden": "a hidden video",
        "playlist": "Playlist “{title}”: {done} done",
        "playlist_failed": ", {failed} failed",
        "hidden_playlist": "a hidden playlist",
        "test": "Tubesy says hello – notifications work.",
    },
}

DEFAULTS = {"ntfy_url": "", "ntfy_token": "", "telegram_token": "", "telegram_chat": "", "on_done": True, "on_failed": True}
SECRETS = ("ntfy_token", "telegram_token")
ROUND = timedelta(minutes=10)


def config_of(user: User) -> dict:
    return {**DEFAULTS, **(user.notify or {})}


def public(user: User) -> dict:
    """The settings for the account page – tokens only as "is set"."""
    cfg = config_of(user)
    out = {k: v for k, v in cfg.items() if k not in SECRETS}
    out.update({f"{k}_set": bool(cfg[k]) for k in SECRETS})
    return out


def _post(url: str, data: bytes, headers: dict) -> None:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def _send_sync(cfg: dict, title: str, text: str) -> list[str]:
    """Sends to every configured service; returns the errors."""
    errors = []
    if cfg["ntfy_url"]:
        headers = {"Title": title.encode("utf-8").decode("latin-1", "replace"), "Tags": "tv"}
        if cfg["ntfy_token"]:
            headers["Authorization"] = f"Bearer {cfg['ntfy_token']}"
        try:
            _post(cfg["ntfy_url"], text.encode("utf-8"), headers)
        except Exception as exc:
            errors.append(f"ntfy: {exc}")
    if cfg["telegram_token"] and cfg["telegram_chat"]:
        url = f"https://api.telegram.org/bot{urllib.parse.quote(cfg['telegram_token'], safe=':')}/sendMessage"
        body = json.dumps({"chat_id": cfg["telegram_chat"], "text": f"{title}\n{text}"}).encode()
        try:
            _post(url, body, {"Content-Type": "application/json"})
        except Exception as exc:
            errors.append(f"Telegram: {exc}")
    return errors


async def send(cfg: dict, title: str, text: str) -> list[str]:
    return await asyncio.to_thread(_send_sync, cfg, title, text)


def _message(db: Session, d: Download) -> str | None:
    """What to say about this finished download, or None (playlist not through yet)."""
    lang = app_settings.get(db, "language")
    t = TEXTS.get(lang, TEXTS["en"])
    if not d.playlist_title:
        title = t["hidden"] if d.hidden else (d.title or d.url)
        return t["done" if d.status == "completed" else "failed"].format(title=title)
    folder = db.query(Download).filter(Download.user_id == d.user_id, Download.playlist_title == d.playlist_title)
    if folder.filter(Download.status.in_(("queued", "downloading", "processing"))).count():
        return None
    # One round = the downloads queued together (a playlist, or one check of a subscription).
    created = d.created_at if d.created_at.tzinfo else d.created_at.replace(tzinfo=timezone.utc)
    siblings = folder.filter(Download.created_at.between(created - ROUND, created + ROUND))
    done = siblings.filter(Download.status == "completed").count()
    failed = siblings.filter(Download.status == "failed").count()
    hidden = siblings.filter(Download.hidden.is_(True)).count() == siblings.count()
    text = t["playlist"].format(title=t["hidden_playlist"] if hidden else d.playlist_title, done=done)
    return text + (t["playlist_failed"].format(failed=failed) if failed else "")


async def download_finished(download_id: int) -> None:
    """Called by the queue after a download completed or failed."""
    try:
        with SessionLocal() as db:
            d = db.get(Download, download_id)
            if d is None or d.status not in ("completed", "failed"):
                return
            cfg = config_of(d.user)
            if not (cfg["ntfy_url"] or (cfg["telegram_token"] and cfg["telegram_chat"])):
                return
            if (d.status == "completed" and not cfg["on_done"]) or (d.status == "failed" and not cfg["on_failed"]):
                return
            text = _message(db, d)
        if text:
            for error in await send(cfg, "Tubesy", text):
                log.warning("Benachrichtigung fehlgeschlagen: %s", error)
    except Exception:
        log.exception("Benachrichtigung für Download %s fehlgeschlagen", download_id)


def test_text(db: Session) -> str:
    return TEXTS.get(app_settings.get(db, "language"), TEXTS["en"])["test"]
