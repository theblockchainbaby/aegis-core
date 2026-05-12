"""Tests for the SQLite storage layer."""
import sqlite3
from pathlib import Path

from aegis_core.storage._conn import connect
from aegis_core.storage.schema import current_schema_version, run_migrations


def test_connect_returns_sqlite_connection(tmp_path: Path):
    conn = connect(tmp_path / "test.db")
    assert isinstance(conn, sqlite3.Connection)
    conn.close()


def test_run_migrations_creates_schema(tmp_path: Path):
    db = tmp_path / "memory.db"
    conn = connect(db)
    run_migrations(conn)
    assert current_schema_version(conn) >= 1
    # Events table exists.
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
    ).fetchall()
    assert rows
    conn.close()


from datetime import UTC, datetime

from aegis_core.messages import PresenceObserved
from aegis_core.storage.events import EventStore


def test_event_store_inserts_and_queries(tmp_path: Path):
    conn = connect(tmp_path / "memory.db")
    run_migrations(conn)
    store = EventStore(conn)

    msg = PresenceObserved(
        timestamp=datetime(2026, 5, 11, 10, 0, 0, tzinfo=UTC),
        present=True,
        source="mmwave",
        confidence=0.93,
    )
    store.insert("senses.presence", msg)

    rows = store.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["subject"] == "senses.presence"
    assert "present" in rows[0]["payload_json"]
    conn.close()


def test_event_store_recent_orders_newest_first(tmp_path: Path):
    conn = connect(tmp_path / "memory.db")
    run_migrations(conn)
    store = EventStore(conn)

    for i in range(3):
        msg = PresenceObserved(
            timestamp=datetime(2026, 5, 11, 10, i, 0, tzinfo=UTC),
            present=True,
            source="mmwave",
            confidence=0.9,
        )
        store.insert("senses.presence", msg)

    rows = store.recent(limit=10)
    assert len(rows) == 3
    # Most recent insert first.
    assert rows[0]["timestamp_utc"] > rows[1]["timestamp_utc"]
    assert rows[1]["timestamp_utc"] > rows[2]["timestamp_utc"]
    conn.close()
