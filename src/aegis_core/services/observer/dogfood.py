"""Dogfood mode — day N of 90 + totals.

Stored as a single key in the existing `meta` table (Plan C schema v1).
No new migration needed.

Note: storage._conn.connect() uses isolation_level=None (autocommit), so
writes via conn.execute() persist immediately and no explicit commit is
needed. If that ever changes, set_dogfood_started_at() must add a commit.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

_KEY = "dogfood_started_at"


@dataclass(frozen=True)
class DogfoodState:
    started_at: datetime | None
    day_of_90: int  # 0 = not started, 1..90 = active, 90 = capped


def set_dogfood_started_at(
    conn: sqlite3.Connection, when: datetime
) -> None:
    conn.execute(
        """
        INSERT INTO meta (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (_KEY, when.isoformat()),
    )


def _read_started_at(conn: sqlite3.Connection) -> datetime | None:
    row = conn.execute(
        "SELECT value FROM meta WHERE key = ?",
        (_KEY,),
    ).fetchone()
    if row is None:
        return None
    return datetime.fromisoformat(row["value"])


def compute_dogfood_state(
    conn: sqlite3.Connection, now: datetime | None = None
) -> DogfoodState:
    started = _read_started_at(conn)
    if started is None:
        return DogfoodState(started_at=None, day_of_90=0)
    now = now or datetime.now(UTC)
    days = (now.date() - started.date()).days + 1
    days = max(0, min(90, days))
    return DogfoodState(started_at=started, day_of_90=days)
