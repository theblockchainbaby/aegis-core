"""EventStore — thin layer over the events table.

Holds no business logic; the memory service decides what to insert and when.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..messages._base import AegisMessage


class EventStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, subject: str, msg: AegisMessage) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO events (timestamp_utc, subject, payload_json)
            VALUES (?, ?, ?)
            """,
            (msg.timestamp.isoformat(), subject, msg.model_dump_json()),
        )
        return int(cur.lastrowid or 0)

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, timestamp_utc, subject, payload_json, created_at_utc
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
        return int(row["c"])
