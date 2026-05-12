from datetime import UTC, datetime
from pathlib import Path

from aegis_core.messages import InterventionClass
from aegis_core.storage._conn import connect
from aegis_core.storage.interventions import InterventionStore
from aegis_core.storage.schema import current_schema_version, run_migrations


def test_schema_v2_creates_interventions_table(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    assert current_schema_version(conn) >= 2
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='interventions'"
    ).fetchall()
    assert rows
    conn.close()


def test_log_aired_inserts_row(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = InterventionStore(conn)
    rid = store.log_aired(
        timestamp=datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC),
        intervention_class=InterventionClass.MEMORY_MAGIC,
        weight=1.0,
        confidence=0.91,
        text="Yesterday you mentioned the landing page.",
    )
    assert rid > 0
    rows = store.query_all()
    assert len(rows) == 1
    assert rows[0]["decision"] == "aired"
    assert rows[0]["text"] == "Yesterday you mentioned the landing page."
    conn.close()


def test_log_vetoed_records_reasons(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = InterventionStore(conn)
    store.log_vetoed(
        timestamp=datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC),
        intervention_class=InterventionClass.AMBIENT_NOTE,
        weight=0.1,
        confidence=0.50,
        text="Long day.",
        reasons=["confidence_below_threshold", "competing_for_attention"],
    )
    rows = store.query_vetoed()
    assert len(rows) == 1
    import json

    assert json.loads(rows[0]["reasons_json"]) == [
        "confidence_below_threshold",
        "competing_for_attention",
    ]
    conn.close()


def test_count_aired_and_vetoed(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = InterventionStore(conn)
    for _ in range(3):
        store.log_aired(
            timestamp=datetime.now(UTC),
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.9,
            text="x",
        )
    for _ in range(7):
        store.log_vetoed(
            timestamp=datetime.now(UTC),
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.4,
            text="x",
            reasons=["low_confidence"],
        )
    assert store.count_aired() == 3
    assert store.count_vetoed() == 7
    conn.close()


def test_mark_acknowledged(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = InterventionStore(conn)
    rid = store.log_aired(
        timestamp=datetime.now(UTC),
        intervention_class=InterventionClass.MEMORY_MAGIC,
        weight=1.0,
        confidence=0.92,
        text="x",
    )
    store.mark_acknowledged(rid, acknowledged=True, at=datetime.now(UTC))
    row = store.query_all()[0]
    assert row["acknowledged"] == 1
    assert row["acknowledged_at_utc"] is not None
    conn.close()
