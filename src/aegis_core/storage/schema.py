"""Schema migrations for the memory store.

Each migration is an idempotent function. The `meta` table tracks which
migrations have been applied. Plan C ships v1: events, moments, themes.
"""
from __future__ import annotations

import sqlite3

CURRENT_VERSION = 1


def run_migrations(conn: sqlite3.Connection) -> None:
    """Bring the DB up to CURRENT_VERSION. Idempotent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    version = current_schema_version(conn)
    if version < 1:
        _migrate_v1(conn)
        _set_version(conn, 1)


def current_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return 0
    return int(row["value"])


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO meta (key, value) VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(version),),
    )


def _migrate_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc TEXT NOT NULL,
            subject TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at_utc TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_events_timestamp ON events(timestamp_utc);
        CREATE INDEX idx_events_subject ON events(subject);

        CREATE TABLE moments (
            id TEXT PRIMARY KEY,
            started_at_utc TEXT NOT NULL,
            ended_at_utc TEXT,
            type TEXT NOT NULL,
            state TEXT NOT NULL,
            summary TEXT,
            signature_json TEXT,
            mood_trace_json TEXT,
            decay_score REAL NOT NULL DEFAULT 0.0,
            reinforcement_count INTEGER NOT NULL DEFAULT 0,
            acknowledged_interventions INTEGER NOT NULL DEFAULT 0,
            vetoed_interventions INTEGER NOT NULL DEFAULT 0,
            last_seen_utc TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_moments_state ON moments(state);
        CREATE INDEX idx_moments_started ON moments(started_at_utc);

        CREATE TABLE themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            reinforcement_count INTEGER NOT NULL DEFAULT 1,
            last_seen_utc TEXT NOT NULL DEFAULT (datetime('now')),
            decay_score REAL NOT NULL DEFAULT 0.0
        );
        CREATE INDEX idx_themes_count ON themes(reinforcement_count);
        """
    )
