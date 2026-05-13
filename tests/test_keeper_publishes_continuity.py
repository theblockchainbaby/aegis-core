import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import ContinuityCandidate, InterventionClass
from aegis_core.services.keeper.service import KeeperService
from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations


def _seed_consolidatable_moment(conn) -> str:
    """Seed a Moment that classify_moment will mark 'consolidated'."""
    store = MomentStore(conn)
    start = datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC)
    mid = store.open_tentative(started_at=start, type_="focus_session")
    store.close(
        mid,
        ended_at=start + timedelta(minutes=20),
        summary="Long focused session on the landing page redesign.",
        signature={
            "posture_events": 14,
            "voice_events": 0,
            "focus_score": 0.92,
        },
    )
    return mid


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_consolidate_publishes_continuity_candidate(
    nats_server, tmp_path: Path
):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    mid = _seed_consolidatable_moment(conn)
    conn.close()

    received: list[ContinuityCandidate] = []

    async def collect(msg: ContinuityCandidate) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "memory.continuity_candidate", ContinuityCandidate, collect
        )
        await listener.flush()

        async with AegisBus.connect(nats_server) as keeper_bus:
            keeper = KeeperService(db_path=db)
            keeper._open_db()
            keeper._bus = keeper_bus  # inject for the sync consolidate_now
            await keeper.consolidate_now_async()  # the new async variant
            await keeper_bus.flush()
            await asyncio.sleep(0.3)

    assert len(received) == 1
    assert received[0].moment_id == mid
    assert "landing" in received[0].moment_summary
    assert received[0].suggested_class == InterventionClass.MEMORY_MAGIC
    assert received[0].confidence > 0.0
