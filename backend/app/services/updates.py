"""Update check: twice a day ask GitHub for the newest Tubesy release.

A stable version only looks at stable releases, a beta also at newer betas.
Development and edge builds have no comparable version and never check.
Nothing is installed automatically; the UI only shows a hint.
"""
import asyncio
import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from .. import config
from ..database import SessionLocal
from . import settings as app_settings

log = logging.getLogger("tubesy.updates")

CHECK_EVERY = 12 * 3600
REPO = "MrLuigi938/tubesy"
# A variable so tests can point it elsewhere.
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=20"

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


@dataclass(frozen=True)
class Version:
    nums: tuple[int, int, int]
    pre: str = ""

    def newer(self, other: "Version") -> bool:
        """Higher numbers win, a release beats its own pre-releases, and
        pre-releases compare part by part (beta.2 > beta.1)."""
        if self.nums != other.nums:
            return self.nums > other.nums
        if self.pre == other.pre:
            return False
        if not self.pre or not other.pre:
            return not self.pre
        a, b = self.pre.split("."), other.pre.split(".")
        for x, y in zip(a, b):
            if x == y:
                continue
            if x.isdigit() and y.isdigit():
                return int(x) > int(y)
            return x > y
        return len(a) > len(b)


def parse_version(value: str | None) -> Version | None:
    m = _VERSION_RE.match((value or "").strip())
    if not m:
        return None
    return Version((int(m[1]), int(m[2]), int(m[3])), m[4] or "")


def newest_release(releases: list[dict], current: str) -> dict | None:
    """The newest release in GitHub's list that is newer than current, or None."""
    cur = parse_version(current)
    if cur is None:
        return None
    best, best_v = None, None
    for r in releases:
        v = parse_version(r.get("tag_name"))
        if r.get("draft") or v is None or (r.get("prerelease") and not cur.pre) or not v.newer(cur):
            continue
        if best_v is None or v.newer(best_v):
            best_v = v
            best = {
                "version": r["tag_name"].lstrip("v"),
                "url": r.get("html_url") or f"https://github.com/{REPO}/releases",
                "published": r.get("published_at"),
            }
    return best


def _fetch() -> list[dict]:
    req = urllib.request.Request(RELEASES_URL, headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"Tubesy/{config.VERSION}",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


class UpdateChecker:
    def __init__(self) -> None:
        self.update: dict | None = None
        self.checked_at: datetime | None = None
        self._task: asyncio.Task | None = None

    @property
    def enabled(self) -> bool:
        return parse_version(config.VERSION) is not None

    async def check(self) -> None:
        with SessionLocal() as db:
            wanted = bool(app_settings.get(db, "update_check"))
        if not wanted or not self.enabled:
            self.update = None
            return
        try:
            releases = await asyncio.to_thread(_fetch)
        except Exception as exc:  # offline, rate limit: try again next round
            log.warning("Update-Prüfung fehlgeschlagen: %s", exc)
            return
        self.update = newest_release(releases, config.VERSION)
        self.checked_at = datetime.now(timezone.utc)
        if self.update:
            log.info("Neue Tubesy-Version verfügbar: %s (installiert: %s)", self.update["version"], config.VERSION)

    async def _loop(self) -> None:
        while True:
            await self.check()
            await asyncio.sleep(CHECK_EVERY)

    def check_soon(self) -> None:
        """Runs a check in the background, e.g. right after the setting was switched."""
        self._soon = asyncio.create_task(self.check())  # keep a reference until it is done

    def start(self) -> None:
        if self.enabled:
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()


checker = UpdateChecker()
