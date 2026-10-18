"""Download queue: schedules queued rows onto yt-dlp subprocesses."""
import asyncio
import logging
import os
import re
import shutil
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config
from ..database import SessionLocal
from ..models import Download, User
from . import settings as app_settings
from .events import hub
from .ytdlp import FILE_PREFIX, POST_PREFIX, PROGRESS_PREFIX, PresetOptions, build_args

log = logging.getLogger("tubesy.downloads")

ACTIVE = ("downloading", "processing")
FINISHED = ("completed", "failed", "canceled")
_EMIT_INTERVAL = 0.5

_POSTPROCESSOR_LABELS = {
    "Merger": "Zusammenführen",
    "FFmpegMerger": "Zusammenführen",
    "ExtractAudio": "Audio extrahieren",
    "FFmpegExtractAudio": "Audio extrahieren",
    "EmbedThumbnail": "Thumbnail einbetten",
    "FFmpegMetadata": "Metadaten",
    "Metadata": "Metadaten",
    "EmbedSubtitle": "Untertitel einbetten",
    "SponsorBlock": "SponsorBlock",
    "ModifyChapters": "Kapitel anpassen",
    "VideoRemuxer": "Remuxen",
    "MoveFiles": "Verschieben",
}


def user_root(user: User) -> Path:
    return config.DOWNLOAD_DIR / user.username


def safe_component(name: str, fallback: str = "Playlist") -> str:
    """Turns a playlist title into a folder name that is valid on SMB/NFS shares."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip(" .")
    return (name[:120].rstrip(" .") or fallback)


def permission_hint() -> str:
    return (
        f"Keine Schreibrechte auf den Download-Ordner (Container läuft als UID {os.getuid()}, "
        f"GID {os.getgid()}). Auf der NAS den Ordner diesem Benutzer geben, z. B. "
        f"'chown -R {os.getuid()}:{os.getgid()} <ordner>', oder PUID/PGID anpassen."
    )


def download_dir_writable() -> bool:
    return os.access(config.DOWNLOAD_DIR, os.W_OK | os.X_OK)


def used_bytes(db: Session, user_id: int) -> int:
    total = (
        db.query(func.coalesce(func.sum(Download.file_size), 0))
        .filter(Download.user_id == user_id, Download.status == "completed")
        .scalar()
    )
    return int(total or 0)


def serialize(d: Download, live: dict | None = None) -> dict:
    data = {
        "id": d.id,
        "user_id": d.user_id,
        "username": d.user.username if d.user else None,
        "url": d.url,
        "video_id": d.video_id,
        "title": d.title,
        "uploader": d.uploader,
        "thumbnail": d.thumbnail,
        "duration": d.duration,
        "preset_name": d.preset_name,
        "mode": (d.options or {}).get("mode", "video"),
        "playlist_title": d.playlist_title,
        "playlist_index": d.playlist_index,
        "subscription_id": d.subscription_id,
        "status": d.status,
        "progress": d.progress,
        "error": d.error,
        "filename": Path(d.file_path).name if d.file_path else None,
        "file_size": d.file_size,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "started_at": d.started_at.isoformat() if d.started_at else None,
        "finished_at": d.finished_at.isoformat() if d.finished_at else None,
        "speed": None,
        "eta": None,
        "downloaded_bytes": None,
        "total_bytes": None,
        "stage": None,
    }
    if live:
        data.update(live)
    return data


def _num(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class DownloadManager:
    def __init__(self) -> None:
        self._procs: dict[int, asyncio.subprocess.Process | None] = {}
        self._tasks: set[asyncio.Task] = set()
        self._cancel_requested: set[int] = set()
        self._live: dict[int, dict] = {}
        self._wake = asyncio.Event()
        self._loop_task: asyncio.Task | None = None

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        with SessionLocal() as db:
            # Anything that was running when the container stopped starts over.
            db.query(Download).filter(Download.status.in_(ACTIVE)).update(
                {"status": "queued", "progress": 0.0}, synchronize_session=False
            )
            db.commit()
        shutil.rmtree(config.TEMP_DIR, ignore_errors=True)
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self._loop_task = asyncio.create_task(self._loop())
        self.wake()

    async def stop(self) -> None:
        if self._loop_task:
            self._loop_task.cancel()
        for proc in self._procs.values():
            if proc and proc.returncode is None:
                proc.kill()
        for task in list(self._tasks):
            task.cancel()

    def wake(self) -> None:
        self._wake.set()

    def live(self, download_id: int) -> dict | None:
        return self._live.get(download_id)

    # -- control -------------------------------------------------------------

    def cancel(self, download_id: int) -> bool:
        """Stops a running download. Returns False if it was not running."""
        if download_id not in self._procs:
            return False
        self._cancel_requested.add(download_id)
        proc = self._procs.get(download_id)
        if proc and proc.returncode is None:
            proc.kill()
        return True

    def cancel_user(self, user_id: int, db: Session) -> None:
        ids = [i for (i,) in db.query(Download.id).filter(Download.user_id == user_id, Download.id.in_(list(self._procs)))]
        for download_id in ids:
            self.cancel(download_id)

    # -- scheduling ----------------------------------------------------------

    async def _loop(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            try:
                self._fill_slots()
            except Exception:
                log.exception("Scheduler error")

    def _fill_slots(self) -> None:
        with SessionLocal() as db:
            cfg = app_settings.get_all(db)
            max_total = max(1, int(cfg["max_concurrent_downloads"]))
            max_user = max(1, int(cfg["max_concurrent_per_user"]))
            free = max_total - len(self._procs)
            if free <= 0:
                return

            per_user: dict[int, int] = {}
            for (uid,) in db.query(Download.user_id).filter(Download.id.in_(list(self._procs))):
                per_user[uid] = per_user.get(uid, 0) + 1

            queued = (
                db.query(Download.id, Download.user_id)
                .filter(Download.status == "queued")
                .order_by(Download.created_at, Download.id)
                .all()
            )
            for download_id, uid in queued:
                if free <= 0:
                    break
                if per_user.get(uid, 0) >= max_user:
                    continue
                per_user[uid] = per_user.get(uid, 0) + 1
                free -= 1
                self._procs[download_id] = None  # reserve the slot before the task runs
                task = asyncio.create_task(self._run(download_id))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    # -- execution -----------------------------------------------------------

    async def _emit(self, d: Download) -> None:
        await hub.publish("download", serialize(d, self._live.get(d.id)), d.user_id)

    async def _run(self, download_id: int) -> None:
        temp = config.TEMP_DIR / str(download_id)
        db = SessionLocal()
        try:
            d = db.get(Download, download_id)
            if d is None or d.status != "queued":
                return
            user = d.user

            quota = user.quota_bytes
            if quota is not None and used_bytes(db, user.id) >= quota:
                d.status, d.error = "failed", "Speicherkontingent erreicht"
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
                await self._emit(d)
                return

            home = user_root(user)
            if d.subfolder:
                home = home / d.subfolder
            try:
                home.mkdir(parents=True, exist_ok=True)
                temp.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                d.status, d.error = "failed", permission_hint()
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
                await self._emit(d)
                return

            prefix = f"{d.playlist_index:03d} - " if d.subfolder and d.playlist_index else ""
            args = build_args(PresetOptions(**d.options), home, temp, d.url, prefix)

            d.status, d.progress, d.error = "downloading", 0.0, None
            d.started_at = datetime.now(timezone.utc)
            db.commit()
            self._live[download_id] = {"stage": "Startet"}
            await self._emit(d)

            proc = await asyncio.create_subprocess_exec(
                *args, cwd=temp, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                limit=1024 * 1024,
            )
            self._procs[download_id] = proc
            if download_id in self._cancel_requested:
                proc.kill()

            output_file, tail = await self._consume(d, proc)
            await proc.wait()

            d.finished_at = datetime.now(timezone.utc)
            if download_id in self._cancel_requested:
                d.status, d.error = "canceled", None
            elif proc.returncode == 0 and output_file and output_file.is_file():
                d.status, d.progress = "completed", 100.0
                d.file_path = str(output_file.relative_to(config.DOWNLOAD_DIR))
                d.file_size = output_file.stat().st_size
            else:
                d.status = "failed"
                errors = [l.removeprefix("ERROR: ") for l in tail if l.startswith("ERROR:")]
                d.error = (errors[-1] if errors else (tail[-1] if tail else f"yt-dlp beendet mit Code {proc.returncode}"))[:2000]
            db.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Download %s crashed", download_id)
            db.rollback()
            d = db.get(Download, download_id)
            if d is not None:
                d.status, d.error = "failed", f"Interner Fehler: {exc}"
                d.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            self._procs.pop(download_id, None)
            self._cancel_requested.discard(download_id)
            self._live.pop(download_id, None)
            shutil.rmtree(temp, ignore_errors=True)
            try:
                d = db.get(Download, download_id)
                if d is not None:
                    await self._emit(d)
            finally:
                db.close()
            self.wake()

    async def _consume(self, d: Download, proc: asyncio.subprocess.Process) -> tuple[Path | None, deque[str]]:
        tail: deque[str] = deque(maxlen=40)
        output_file: Path | None = None
        streams: list[str] = []
        last_emit = 0.0
        live = self._live[d.id]
        db = SessionLocal.object_session(d)

        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            if not line:
                continue

            if line.startswith(PROGRESS_PREFIX):
                status, done, total, estimate, speed, eta, fmt = (line[len(PROGRESS_PREFIX):].split("|") + [""] * 7)[:7]
                if fmt not in streams:
                    streams.append(fmt)
                done_n, total_n = _num(done), _num(total) or _num(estimate)
                live.update({
                    "downloaded_bytes": done_n,
                    "total_bytes": total_n,
                    "speed": _num(speed),
                    "eta": _num(eta),
                    "stage": f"Download Stream {len(streams)}" if len(streams) > 1 else "Download",
                })
                if total_n and done_n is not None:
                    d.progress = round(min(100.0, done_n / total_n * 100), 1)
                if status == "finished":
                    d.progress = 100.0
            elif line.startswith(POST_PREFIX):
                status, name = (line[len(POST_PREFIX):].split("|") + [""])[:2]
                if status == "started":
                    if d.status != "processing":
                        d.status = "processing"
                        db.commit()
                    live.update({"stage": _POSTPROCESSOR_LABELS.get(name, name), "speed": None, "eta": None})
            elif line.startswith(FILE_PREFIX):
                candidate = Path(line[len(FILE_PREFIX):]).resolve()
                if candidate.is_relative_to(config.DOWNLOAD_DIR):
                    output_file = candidate
                continue
            else:
                tail.append(line)
                continue

            now = time.monotonic()
            if now - last_emit >= _EMIT_INTERVAL:
                last_emit = now
                await self._emit(d)
        return output_file, tail


manager = DownloadManager()
