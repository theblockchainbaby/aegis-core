import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from aegis_core.services.observer.snapshots import (
    generate_daily_snapshot,
    write_daily_snapshot,
)
from aegis_core.storage._conn import connect
from aegis_core.storage.interventions import InterventionStore
from aegis_core.storage.schema import run_migrations


def _seed_one_aired_and_one_vetoed(conn) -> None:
    store = InterventionStore(conn)
    today = datetime(2026, 5, 12, 10, 0, 0, tzinfo=UTC)
    store.log_aired(
        timestamp=today,
        intervention_class="memory_magic",
        weight=1.0,
        confidence=0.92,
        text="Yesterday you mentioned the landing page.",
    )
    store.log_vetoed(
        timestamp=today,
        intervention_class="ambient_note",
        weight=0.1,
        confidence=0.4,
        text="x",
        reasons=["confidence_below_threshold"],
    )


def test_daily_snapshot_counts_aired_and_vetoed(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    _seed_one_aired_and_one_vetoed(conn)

    snap = generate_daily_snapshot(date(2026, 5, 12), conn)
    conn.close()

    assert snap["date"] == "2026-05-12"
    assert snap["interventions"]["aired"] == 1
    assert snap["interventions"]["vetoed"] == 1
    assert "Yesterday you mentioned" in (
        snap["aired_utterances"][0]["text"]
    )


def test_write_daily_snapshot_dumps_json(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    _seed_one_aired_and_one_vetoed(conn)
    out_dir = tmp_path / "snapshots"

    path = write_daily_snapshot(date(2026, 5, 12), conn, out_dir=out_dir)
    conn.close()

    assert path.exists()
    assert path.name == "2026-05-12.json"
    data = json.loads(path.read_text())
    assert data["date"] == "2026-05-12"


def test_snapshot_excludes_events_outside_day(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    store = InterventionStore(conn)
    # One on the target day, one before, one after.
    store.log_aired(
        timestamp=datetime(2026, 5, 12, 10, 0, 0, tzinfo=UTC),
        intervention_class="memory_magic", weight=1.0, confidence=0.9, text="today",
    )
    store.log_aired(
        timestamp=datetime(2026, 5, 11, 10, 0, 0, tzinfo=UTC),
        intervention_class="memory_magic", weight=1.0, confidence=0.9, text="yesterday",
    )
    store.log_aired(
        timestamp=datetime(2026, 5, 13, 10, 0, 0, tzinfo=UTC),
        intervention_class="memory_magic", weight=1.0, confidence=0.9, text="tomorrow",
    )

    snap = generate_daily_snapshot(date(2026, 5, 12), conn)
    conn.close()
    texts = [u["text"] for u in snap["aired_utterances"]]
    assert texts == ["today"]
