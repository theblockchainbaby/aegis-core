import json
from datetime import UTC, datetime
from pathlib import Path

from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations


def _now():
    return datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC)


def test_open_tentative_returns_moment_id(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = MomentStore(conn)

    mid = store.open_tentative(
        started_at=_now(),
        type_="observing_window",
    )

    assert isinstance(mid, str)
    assert mid.startswith("moment_")


def test_close_sets_ended_at_and_summary(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = MomentStore(conn)

    mid = store.open_tentative(
        started_at=_now(),
        type_="focus_session",
    )
    ended = datetime(2026, 5, 11, 9, 15, 0, tzinfo=UTC)
    store.close(
        mid,
        ended_at=ended,
        summary="15 minutes at desk, screen-focused.",
        signature={"focus_score": 0.9, "voice_events": 0},
    )

    row = store.get(mid)
    assert row is not None
    assert row["ended_at_utc"] == ended.isoformat()
    assert row["summary"] == "15 minutes at desk, screen-focused."
    sig = json.loads(row["signature_json"])
    assert sig["focus_score"] == 0.9


def test_promote_transitions_state(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = MomentStore(conn)

    mid = store.open_tentative(started_at=_now(), type_="x")
    store.promote(mid, new_state="consolidated")
    row = store.get(mid)
    assert row["state"] == "consolidated"


def test_query_filters_by_state(tmp_path: Path):
    conn = connect(tmp_path / "m.db")
    run_migrations(conn)
    store = MomentStore(conn)

    a = store.open_tentative(started_at=_now(), type_="a")
    b = store.open_tentative(started_at=_now(), type_="b")
    store.promote(a, new_state="consolidated")

    tentative = store.query(state="tentative")
    consolidated = store.query(state="consolidated")
    assert {r["id"] for r in consolidated} == {a}
    assert {r["id"] for r in tentative} == {b}
