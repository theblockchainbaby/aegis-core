"""InterventionStore — thin layer over the interventions log table.

Every Steward decision is recorded here. Plan F's observer cockpit reads
this table.

The decision column accepts three values, enforced by a SQLite CHECK
constraint:
- 'aired'       — proposal cleared the gate; voice.speak was published
- 'vetoed'      — proposal failed the gate; reasons logged
- 'soft_vetoed' — RESERVED (Plan E). "Not now, but ask again later."
                  Plan D never emits this value; the enum is reserved at
                  the schema level so the future delayed-utterance
                  mechanism doesn't require a schema migration.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

# Documented decision enum; mirrored by the SQLite CHECK constraint.
VALID_DECISIONS = ("aired", "vetoed", "soft_vetoed")


class InterventionStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def log_aired(
        self,
        timestamp: datetime,
        intervention_class: str,
        weight: float,
        confidence: float,
        text: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO interventions
                (timestamp_utc, intervention_class, weight, confidence, text,
                 decision, reasons_json, acknowledged)
            VALUES (?, ?, ?, ?, ?, 'aired', NULL, NULL)
            """,
            (
                timestamp.isoformat(),
                str(intervention_class),
                weight,
                confidence,
                text,
            ),
        )
        return int(cur.lastrowid or 0)

    def log_vetoed(
        self,
        timestamp: datetime,
        intervention_class: str,
        weight: float,
        confidence: float,
        text: str,
        reasons: list[str],
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO interventions
                (timestamp_utc, intervention_class, weight, confidence, text,
                 decision, reasons_json, acknowledged)
            VALUES (?, ?, ?, ?, ?, 'vetoed', ?, NULL)
            """,
            (
                timestamp.isoformat(),
                str(intervention_class),
                weight,
                confidence,
                text,
                json.dumps(reasons),
            ),
        )
        return int(cur.lastrowid or 0)

    def mark_acknowledged(
        self,
        intervention_id: int,
        acknowledged: bool,
        at: datetime,
    ) -> None:
        self._conn.execute(
            """
            UPDATE interventions
               SET acknowledged = ?, acknowledged_at_utc = ?
             WHERE id = ?
            """,
            (1 if acknowledged else 0, at.isoformat(), intervention_id),
        )

    def query_all(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM interventions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_aired(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM interventions WHERE decision='aired'
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def query_vetoed(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM interventions WHERE decision='vetoed'
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_aired(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM interventions WHERE decision='aired'"
        ).fetchone()
        return int(row["c"])

    def count_vetoed(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM interventions WHERE decision='vetoed'"
        ).fetchone()
        return int(row["c"])
