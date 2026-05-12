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


from aegis_core.storage.moments import MomentStore


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_memory_opens_and_closes_moment_on_state_transition(
    nats_server,
    tmp_path: Path,
):
    db_path = tmp_path / "memory.db"
    service = MemoryService(nats_url=nats_server, db_path=db_path)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as publisher:
        # Open: DORMANT → OBSERVING
        await publisher.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.DORMANT,
                current=PresenceState.OBSERVING,
                reason="presence_detected",
            ),
        )
        await publisher.flush()
        # Some posture events to populate the signature.
        for ms in [0.03, 0.04, 0.02]:
            await publisher.publish(
                "senses.posture",
                PostureObserved(
                    timestamp=datetime.now(UTC),
                    at_desk=True,
                    gaze="screen",
                    movement_score=ms,
                ),
            )
        await publisher.flush()
        await asyncio.sleep(0.3)

        # Close: OBSERVING → DORMANT
        await publisher.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.OBSERVING,
                current=PresenceState.DORMANT,
                reason="presence_lost",
            ),
        )
        await publisher.flush()
        await asyncio.sleep(0.3)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    conn = connect(db_path)
    run_migrations(conn)
    moments = MomentStore(conn).query()
    conn.close()

    assert len(moments) == 1
    moment = moments[0]
    assert moment["state"] == "tentative"
    assert moment["ended_at_utc"] is not None
    # Signature should have captured 3 posture events.
    import json as _json

    sig = _json.loads(moment["signature_json"])
    assert sig["posture_events"] == 3
    assert sig["focus_score"] > 0.0


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_memory_query_api(nats_server, tmp_path: Path):
    db_path = tmp_path / "memory.db"
    service = MemoryService(nats_url=nats_server, db_path=db_path)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as publisher:
        for _ in range(3):
            await publisher.publish(
                "senses.presence",
                PresenceObserved(
                    timestamp=datetime.now(UTC),
                    present=True,
                    source="mmwave",
                    confidence=0.9,
                ),
            )
        await publisher.flush()
        await asyncio.sleep(0.3)

    events = service.query_recent_events(limit=10)
    assert len(events) == 3
    assert all(e["subject"] == "senses.presence" for e in events)

    moments = service.query_moments()
    assert isinstance(moments, list)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)
