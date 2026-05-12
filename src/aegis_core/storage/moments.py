"""MomentStore — moments table CRUD.

Owns the data. Plan C's keeper service decides WHEN to promote/fade; this
module just exposes the SQL primitives.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

VALID_STATES = ("tentative", "fading", "consolidated")


def _moment_id(started_at: datetime, type_: str) -> str:
    """Stable-ish ID: timestamp + type + short uuid for uniqueness in tests."""
    ts = started_at.strftime("%Y-%m-%dT%H-%M-%S")
    short = uuid.uuid4().hex[:6]
    return f"moment_{ts}_{type_}_{short}"


class MomentStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def open_tentative(
        self,
        started_at: datetime,
        type_: str,
    ) -> str:
        mid = _moment_id(started_at, type_)
        self._conn.execute(
            """
            INSERT INTO moments (id, started_at_utc, type, state)
            VALUES (?, ?, ?, 'tentative')
            """,
            (mid, started_at.isoformat(), type_),
        )
        return mid

    def close(
        self,
        moment_id: str,
        ended_at: datetime,
        summary: str | None = None,
        signature: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE moments
               SET ended_at_utc = ?,
                   summary = ?,
                   signature_json = ?
             WHERE id = ?
            """,
            (
                ended_at.isoformat(),
                summary,
                json.dumps(signature) if signature is not None else None,
                moment_id,
            ),
        )

    def promote(self, moment_id: str, new_state: str) -> None:
        if new_state not in VALID_STATES:
            raise ValueError(f"invalid state: {new_state!r}")
        self._conn.execute(
            "UPDATE moments SET state = ? WHERE id = ?",
            (new_state, moment_id),
        )

    def get(self, moment_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM moments WHERE id = ?",
            (moment_id,),
        ).fetchone()
        return dict(row) if row else None

    def query(
        self,
        state: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if state is not None:
            rows = self._conn.execute(
                """
                SELECT * FROM moments WHERE state = ?
                ORDER BY started_at_utc DESC LIMIT ?
                """,
                (state, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM moments
                ORDER BY started_at_utc DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, moment_id: str) -> None:
        self._conn.execute("DELETE FROM moments WHERE id = ?", (moment_id,))
