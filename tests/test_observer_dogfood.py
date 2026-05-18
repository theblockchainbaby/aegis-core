from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.services.observer.dogfood import (
    DogfoodState,
    compute_dogfood_state,
    set_dogfood_started_at,
)
from aegis_core.storage._conn import connect
from aegis_core.storage.schema import run_migrations


def test_set_and_read_started_at(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    started = datetime(2026, 5, 1, 9, 0, 0, tzinfo=UTC)
    set_dogfood_started_at(conn, started)

    state = compute_dogfood_state(conn, now=datetime(2026, 5, 15, 9, 0, 0, tzinfo=UTC))
    conn.close()
    assert isinstance(state, DogfoodState)
    assert state.day_of_90 == 15  # 1-based; day 1 = May 1
    assert state.started_at == started


def test_no_started_at_means_inactive(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    state = compute_dogfood_state(conn, now=datetime(2026, 5, 15, 9, 0, 0, tzinfo=UTC))
    conn.close()
    assert state.day_of_90 == 0
    assert state.started_at is None


def test_day_count_caps_at_90(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    set_dogfood_started_at(conn, datetime(2026, 1, 1, tzinfo=UTC))
    state = compute_dogfood_state(conn, now=datetime(2026, 12, 31, tzinfo=UTC))
    conn.close()
    assert state.day_of_90 == 90


@pytest.mark.asyncio
async def test_api_dogfood_endpoint(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer

    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    set_dogfood_started_at(conn, datetime(2026, 5, 1, tzinfo=UTC))
    conn.close()

    app = build_app(buffer=EventRingBuffer(capacity=50), db_path=db)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/dogfood")
    body = r.json()
    assert body["day_of_90"] >= 1
    assert body["started_at"] is not None
