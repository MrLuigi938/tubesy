import hashlib
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Used to keep login timing constant when the username does not exist.
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RateLimiter:
    """Sliding-window limiter kept in memory (good enough for a single container)."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        return hits

    def blocked(self, key: str) -> int:
        """Returns seconds until the key may try again, 0 if not blocked."""
        now = time.monotonic()
        hits = self._prune(key, now)
        if len(hits) >= self.limit:
            return int(hits[0] + self.window - now) + 1
        return 0

    def hit(self, key: str) -> None:
        self._hits[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


login_ip_limiter = RateLimiter(limit=20, window_seconds=15 * 60)
login_user_limiter = RateLimiter(limit=8, window_seconds=15 * 60)
register_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
