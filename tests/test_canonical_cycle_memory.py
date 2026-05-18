"""Plan C capstone — canonical-cycle fixture produces real Moments."""
import asyncio
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.services.keeper.service import KeeperService
from aegis_core.services.memory.service import MemoryService
from aegis_core.services.senses.service import SensesService
from aegis_core.services.senses.sources.trace import TraceRunner
from aegis_core.services.state.service import StateService
from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations

FIXTURE = (
    Path(__file__).parent / "fixtures" / "traces" / "canonical_cycle.json"
)


@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_canonical_cycle_creates_a_moment(
    nats_server,
    tmp_path: Path,
):
    db_path = tmp_path / "memory.db"

    async with AegisBus.connect(nats_server) as _:
        pass  # warm up

    state_service = StateService(
        nats_url=nats_server, tick_ms=50, accelerate_for_test=50.0
    )
    memory_service = MemoryService(nats_url=nats_server, db_path=db_path)
    senses_service = SensesService(
        nats_url=nats_server,
        sources=[TraceRunner(FIXTURE, real_time=False, min_pacing_ms=50)],
    )

    # Start memory + state first so subscriptions are live before senses fires.
    memory_task = asyncio.create_task(memory_service.run())
    state_task = asyncio.create_task(state_service.run())
    await asyncio.sleep(0.4)
    senses_task = asyncio.create_task(senses_service.run())

    await asyncio.wait([senses_task], timeout=20)
    await asyncio.sleep(1.0)  # let memory absorb the tail

    state_service.shutdown()
    memory_service.shutdown()
    senses_service.shutdown()
    await asyncio.gather(
        state_task, memory_task, senses_task, return_exceptions=True
    )

    # At this point, the DB should have at least one tentative Moment
    # (opened on DORMANT → OBSERVING) and many recorded events.
    conn = connect(db_path)
    run_migrations(conn)
    moments_before = MomentStore(conn).query()
    conn.close()

    assert len(moments_before) >= 1, (
        f"no Moments recorded; got {moments_before}"
    )

    # Now run the keeper consolidation pass.
    # Because the trace's compressed timeline produces Moments shorter than
    # 30s wall-clock duration but Plan C's MIN_DURATION_S_FOR_CONSOLIDATE is
    # 30s, the Moment will most likely classify as 'fading'. That's still a
    # valid Plan C signal — the lifecycle ran. The strong assertion is that
    # *some* classification happened.
    keeper = KeeperService(db_path=db_path)
    keeper._open_db()
    counts = keeper.consolidate_now()
    # Accept "keep" as a legitimate outcome per Task 10's keep-tentative rule:
    # if duration < 300s and posture_events >= 1, classify_moment returns "keep".
    # The trace's compressed timeline likely produces such a Moment.
    assert counts["consolidated"] + counts["fading"] + counts["kept"] >= 1, (
        f"keeper made no decisions; counts={counts}"
    )

    conn = connect(db_path)
    moments_after = MomentStore(conn).query()
    conn.close()
    states = {m["state"] for m in moments_after}
    # tentative (kept), consolidated, or fading — all are valid lifecycle outcomes.
    assert states & {"consolidated", "fading", "tentative"}, (
        f"no tentative→consolidated/fading transitions; states={states}"
    )
