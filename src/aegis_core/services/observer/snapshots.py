"""Daily snapshot generator — pulls all observable data for a date.

Pure functions over a SQLite connection. The observer service writes the
result to data/snapshots/YYYY-MM-DD.json. Plan F ships daily granularity
only — no weekly aggregation, no list endpoint. The filesystem listing
of `data/snapshots/` is the source of truth for "what days exist."
Spec §10.1 favors per-day granularity over aggregate dashboards anyway.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


def _bounds(d: date) -> tuple[str, str]:
    start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def generate_daily_snapshot(
    d: date, conn: sqlite3.Connection
) -> dict[str, Any]:
    start, end = _bounds(d)

    aired_rows = conn.execute(
        """
        SELECT timestamp_utc, intervention_class, weight, confidence, text
          FROM interventions
         WHERE decision = 'aired'
           AND timestamp_utc >= ?
           AND timestamp_utc < ?
         ORDER BY timestamp_utc
        """,
        (start, end),
    ).fetchall()
    vetoed_rows = conn.execute(
        """
        SELECT timestamp_utc, intervention_class, weight, confidence, text,
               reasons_json
          FROM interventions
         WHERE decision = 'vetoed'
           AND timestamp_utc >= ?
           AND timestamp_utc < ?
         ORDER BY timestamp_utc
        """,
        (start, end),
    ).fetchall()
    moment_rows = conn.execute(
        """
        SELECT id, started_at_utc, ended_at_utc, type, state, summary
          FROM moments
         WHERE started_at_utc >= ?
           AND started_at_utc < ?
         ORDER BY started_at_utc
        """,
        (start, end),
    ).fetchall()
    event_rows = conn.execute(
        """
        SELECT timestamp_utc, subject, payload_json
          FROM events
         WHERE timestamp_utc >= ?
           AND timestamp_utc < ?
         ORDER BY timestamp_utc
        """,
        (start, end),
    ).fetchall()

    return {
        "date": d.isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "interventions": {
            "aired": len(aired_rows),
            "vetoed": len(vetoed_rows),
        },
        "aired_utterances": [
            {
                "timestamp": r["timestamp_utc"],
                "intervention_class": r["intervention_class"],
                "weight": r["weight"],
                "confidence": r["confidence"],
                "text": r["text"],
            }
            for r in aired_rows
        ],
        "vetoed_proposals": [
            {
                "timestamp": r["timestamp_utc"],
                "intervention_class": r["intervention_class"],
                "weight": r["weight"],
                "confidence": r["confidence"],
                "text": r["text"],
                "reasons": json.loads(r["reasons_json"] or "[]"),
            }
            for r in vetoed_rows
        ],
        "moments": [
            {
                "id": r["id"],
                "type": r["type"],
                "state": r["state"],
                "started_at": r["started_at_utc"],
                "ended_at": r["ended_at_utc"],
                "summary": r["summary"],
            }
            for r in moment_rows
        ],
        "event_total": len(event_rows),
    }


def write_daily_snapshot(
    d: date, conn: sqlite3.Connection, out_dir: str | Path
) -> Path:
    snap = generate_daily_snapshot(d, conn)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{d.isoformat()}.json"
    out_path.write_text(json.dumps(snap, indent=2))
    return out_path
