"""ThemeStore — themes table CRUD.

Simple keyword tokens with a reinforcement count and a decay primitive.
Plan E will replace this with semantic-embedding-keyed themes.
"""
from __future__ import annotations

import sqlite3
from typing import Any


class ThemeStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, key: str) -> None:
        self._conn.execute(
            """
            INSERT INTO themes (key, reinforcement_count, last_seen_utc)
            VALUES (?, 1, datetime('now'))
            ON CONFLICT(key) DO UPDATE
              SET reinforcement_count = reinforcement_count + 1,
                  last_seen_utc = datetime('now')
            """,
            (key,),
        )

    def query(self, min_count: int = 1, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM themes
             WHERE reinforcement_count >= ?
             ORDER BY reinforcement_count DESC, key ASC
             LIMIT ?
            """,
            (min_count, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def decay(self, decrement: int = 1) -> None:
        self._conn.execute(
            "UPDATE themes SET reinforcement_count = reinforcement_count - ?",
            (decrement,),
        )
        self._conn.execute("DELETE FROM themes WHERE reinforcement_count <= 0")
