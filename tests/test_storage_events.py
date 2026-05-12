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
