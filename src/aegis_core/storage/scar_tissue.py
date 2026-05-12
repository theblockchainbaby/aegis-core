"""ScarTissueStore — per-intervention-class confidence-penalty persistence.

Spec §6: vetoed_repeat_penalty=0.03, unacknowledged_repeat_penalty=0.05,
recovery_on_acknowledgment=0.07, floor=0.00, cap=0.15. Bounded and
deterministic (no randomness).
"""
from __future__ import annotations

import sqlite3


class ScarTissueStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_penalty(self, intervention_class: str) -> float:
        row = self._conn.execute(
            "SELECT confidence_penalty FROM scar_tissue WHERE intervention_class = ?",
            (intervention_class,),
        ).fetchone()
        if row is None:
            return 0.0
        return float(row["confidence_penalty"])

    def _upsert(self, intervention_class: str, new_value: float) -> None:
        self._conn.execute(
            """
            INSERT INTO scar_tissue (intervention_class, confidence_penalty, last_updated_utc)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(intervention_class) DO UPDATE
              SET confidence_penalty = excluded.confidence_penalty,
                  last_updated_utc = excluded.last_updated_utc
            """,
            (intervention_class, new_value),
        )

    def bump_veto(
        self, intervention_class: str, by: float = 0.03, cap: float = 0.15
    ) -> None:
        current = self.get_penalty(intervention_class)
        self._upsert(intervention_class, min(cap, current + by))

    def bump_unacknowledged(
        self, intervention_class: str, by: float = 0.05, cap: float = 0.15
    ) -> None:
        current = self.get_penalty(intervention_class)
        self._upsert(intervention_class, min(cap, current + by))

    def recover(
        self, intervention_class: str, by: float = 0.07, floor: float = 0.0
    ) -> None:
        current = self.get_penalty(intervention_class)
        self._upsert(intervention_class, max(floor, current - by))

    def all_classes(self) -> dict[str, float]:
        rows = self._conn.execute(
            "SELECT intervention_class, confidence_penalty FROM scar_tissue"
        ).fetchall()
        return {r["intervention_class"]: float(r["confidence_penalty"]) for r in rows}
