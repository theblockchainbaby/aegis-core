import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
)
from aegis_core.services.memory.service import MemoryService
from aegis_core.storage._conn import connect
from aegis_core.storage.events import EventStore
from aegis_core.storage.schema import run_migrations


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_memory_records_senses_and_state_events(
    nats_server,
    tmp_path: Path,
):
    db_path = tmp_path / "memory.db"
    service = MemoryService(nats_url=nats_server, db_path=db_path)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as publisher:
        await publisher.publish(
            "senses.presence",
            PresenceObserved(
                timestamp=datetime.now(UTC),
                present=True,
                source="mmwave",
                confidence=0.95,
            ),
        )
        await publisher.publish(
            "senses.posture",
            PostureObserved(
                timestamp=datetime.now(UTC),
                at_desk=True,
                gaze="screen",
                movement_score=0.1,
            ),
        )
        await publisher.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.DORMANT,
                current=PresenceState.OBSERVING,
                reason="test",
            ),
        )
        await publisher.flush()
        await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    # Inspect the DB.
    conn = connect(db_path)
    run_migrations(conn)
    rows = EventStore(conn).recent(limit=10)
    conn.close()

    subjects = {r["subject"] for r in rows}
    assert subjects == {
        "senses.presence",
        "senses.posture",
        "state.changed",
    }
