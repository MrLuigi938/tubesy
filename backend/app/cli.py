"""Command line helpers for the server.

    python -m app.cli reset-password <user> <new-password>

In Docker: docker exec -it tubesy python -m app.cli reset-password <user> <new-password>
"""
import sys

from .database import Base, SessionLocal, engine
from .models import User, UserSession
from .routers.auth import validate_password
from .security import hash_password


def reset_password(username: str, password: str) -> int:
    try:
        validate_password(password)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username.strip().lower()).one_or_none()
        if user is None:
            names = ", ".join(u.username for u in db.query(User).order_by(User.username)) or "none"
            print(f"Error: no user '{username}' (users: {names})", file=sys.stderr)
            return 1
        user.password_hash = hash_password(password)
        user.is_active = True
        # Signed-in devices must log in again with the new password.
        db.query(UserSession).filter_by(user_id=user.id).delete()
        db.commit()
    print(f"Password for '{user.username}' has been reset; the account is active.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "reset-password":
        return reset_password(argv[1], argv[2])
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
