import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import ContinuityCandidate
from aegis_core.services.keeper.service import KeeperService
from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_keeper_periodic_consolidation_loop(nats_server, tmp_path: Path):
    """The keeper's main loop should periodically run consolidate_now_async,
    promoting tentative Moments and publishing continuity candidate events."""
    db_path = tmp_path / "m.db"
    conn = connect(db_path)
    run_migrations(conn)

    store = MomentStore(conn)
    started = datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC)
    mid = store.open_tentative(started_at=started, type_="focus_session")
    store.close(
        mid,
        ended_at=started + timedelta(minutes=30),
        summary="Long focused session on the landing page redesign.",
        signature={
            "posture_events": 60,
            "voice_events": 0,
            "focus_score": 0.85,
        },
    )
    conn.close()

    received_candidates: list[ContinuityCandidate] = []

    async def on_candidate(msg: ContinuityCandidate) -> None:
        received_candidates.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "memory.continuity_candidate", ContinuityCandidate, on_candidate
        )
        await listener.flush()

        service = KeeperService(
            nats_url=nats_server,
            db_path=db_path,
            consolidate_interval_seconds=0.1,
        )
        task = asyncio.create_task(service.run())

        # Wait for at least one consolidation pass.
        for _ in range(50):
            if received_candidates:
                break
            await asyncio.sleep(0.1)

        service.shutdown()
        await asyncio.wait_for(task, timeout=5)

    # Verify the seeded Moment was promoted.
    conn = connect(db_path)
    store = MomentStore(conn)
    rows = store.query(state="consolidated", limit=10)
    conn.close()

    assert len(rows) >= 1, (
        f"expected the seeded Moment to be consolidated, got {len(rows)} consolidated rows"
    )
    assert any(r["id"] == mid for r in rows), (
        f"seeded Moment {mid} not found in consolidated set"
    )
    assert len(received_candidates) >= 1, (
        "expected at least one memory.continuity_candidate event"
    )
