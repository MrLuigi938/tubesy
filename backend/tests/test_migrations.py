import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401 – registers the tables
from app.database import Base, migrate

FIXTURES = Path(__file__).parent / "fixtures"


def test_database_of_1_0_0_is_brought_up_to_date(tmp_path: Path):
    """A 1.0.0 database with data gets the new columns, with their defaults."""
    db = tmp_path / "old.db"
    con = sqlite3.connect(db)
    con.executescript((FIXTURES / "schema-1.0.0.sql").read_text(encoding="utf-8"))
    con.execute("INSERT INTO users (id, username, password_hash, role, is_active, created_at) VALUES (1, 'alt', 'x', 'admin', 1, '2026-10-26')")
    con.execute(
        "INSERT INTO downloads (id, user_id, url, options, status, progress, created_at) "
        "VALUES (1, 1, 'https://example.com', '{}', 'completed', 100, '2026-10-26')"
    )
    con.commit()
    con.close()

    engine = create_engine(f"sqlite:///{db}")
    added = migrate(engine)
    assert "downloads.hidden" in added and "users.auto_hide_adult" in added

    # Every column of the current models exists now …
    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if insp.has_table(table.name):
            have = {c["name"] for c in insp.get_columns(table.name)}
            assert {c.name for c in table.columns} <= have, table.name
    # … old rows got the defaults, and a second run changes nothing.
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT hidden FROM downloads WHERE id = 1").scalar() == 0
        assert conn.exec_driver_sql("SELECT auto_hide_adult FROM users WHERE id = 1").scalar() == 1
    assert migrate(engine) == []
    engine.dispose()
