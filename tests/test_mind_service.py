import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    ContinuityCandidate,
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from aegis_core.services.mind.service import MindService


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mind_proposes_on_reflective_with_candidate(
    nats_server, tmp_path: Path
):
    db = tmp_path / "m.db"
    service = MindService(nats_url=nats_server, db_path=db)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[UtteranceProposal] = []

    async def collect(msg: UtteranceProposal) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "mind.utterance_proposal", UtteranceProposal, collect
        )
        await listener.flush()

        async with AegisBus.connect(nats_server) as publisher:
            # Seed a continuity candidate first.
            await publisher.publish(
                "memory.continuity_candidate",
                ContinuityCandidate(
                    timestamp=datetime.now(UTC),
                    moment_id="moment_test",
                    moment_summary="Landing page redesign session.",
                    themes=["landing", "redesign"],
                    confidence=0.9,
                    suggested_class=InterventionClass.MEMORY_MAGIC,
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.2)

            # Now drive REFLECTIVE.
            await publisher.publish(
                "state.changed",
                StateChanged(
                    timestamp=datetime.now(UTC),
                    previous=PresenceState.ATTENTIVE,
                    current=PresenceState.REFLECTIVE,
                    reason="memory_candidate",
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 1
    assert received[0].intervention_class == InterventionClass.MEMORY_MAGIC


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mind_retrieves_existing_consolidated_moment_on_reflective(
    nats_server, tmp_path: Path
):
    """No ContinuityCandidate event arrives — mind must STILL surface a
    Memory Magic proposal by querying the memory store directly.

    Critical: keeper runs nightly, but reflective cognition is runtime.
    """
    from datetime import timedelta
    from aegis_core.storage._conn import connect
    from aegis_core.storage.moments import MomentStore
    from aegis_core.storage.schema import run_migrations

    db = tmp_path / "m.db"
    # Seed a consolidated Moment directly (no keeper, no event).
    conn = connect(db)
    run_migrations(conn)
    store = MomentStore(conn)
    start = datetime.now(UTC) - timedelta(hours=20)
    mid = store.open_tentative(started_at=start, type_="focus_session")
    store.close(
        mid,
        ended_at=start + timedelta(minutes=22),
        summary="Long focused session on the landing page redesign.",
        signature={
            "posture_events": 14,
            "voice_events": 0,
            "focus_score": 0.92,
        },
    )
    store.promote(mid, new_state="consolidated")
    conn.close()

    service = MindService(nats_url=nats_server, db_path=db)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[UtteranceProposal] = []

    async def collect(msg: UtteranceProposal) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "mind.utterance_proposal", UtteranceProposal, collect
        )
        await listener.flush()

        async with AegisBus.connect(nats_server) as publisher:
            # NO ContinuityCandidate published. Just drive REFLECTIVE.
            await publisher.publish(
                "state.changed",
                StateChanged(
                    timestamp=datetime.now(UTC),
                    previous=PresenceState.ATTENTIVE,
                    current=PresenceState.REFLECTIVE,
                    reason="memory_candidate",
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 1, (
        "mind must retrieve the consolidated Moment even without a "
        "ContinuityCandidate event"
    )
    assert received[0].intervention_class == InterventionClass.MEMORY_MAGIC


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mind_prefers_fresh_event_over_retrieval(
    nats_server, tmp_path: Path
):
    """When BOTH a fresh ContinuityCandidate event AND a queryable
    consolidated Moment exist, mind uses the event (it's more specific to
    the current cycle).
    """
    from datetime import timedelta
    from aegis_core.storage._conn import connect
    from aegis_core.storage.moments import MomentStore
    from aegis_core.storage.schema import run_migrations

    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    store = MomentStore(conn)
    start = datetime.now(UTC) - timedelta(hours=20)
    mid = store.open_tentative(started_at=start, type_="focus_session")
    store.close(
        mid,
        ended_at=start + timedelta(minutes=22),
        summary="An older consolidated Moment about an outdated project.",
        signature={"posture_events": 14, "focus_score": 0.85},
    )
    store.promote(mid, new_state="consolidated")
    conn.close()

    service = MindService(nats_url=nats_server, db_path=db)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[UtteranceProposal] = []

    async def collect(msg: UtteranceProposal) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "mind.utterance_proposal", UtteranceProposal, collect
        )
        await listener.flush()

        async with AegisBus.connect(nats_server) as publisher:
            # A fresh, more recent ContinuityCandidate is published first.
            await publisher.publish(
                "memory.continuity_candidate",
                ContinuityCandidate(
                    timestamp=datetime.now(UTC),
                    moment_id="moment_fresh",
                    moment_summary="A fresh session about something new today.",
                    themes=["new"],
                    confidence=0.9,
                    suggested_class=InterventionClass.MEMORY_MAGIC,
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.2)

            await publisher.publish(
                "state.changed",
                StateChanged(
                    timestamp=datetime.now(UTC),
                    previous=PresenceState.ATTENTIVE,
                    current=PresenceState.REFLECTIVE,
                    reason="memory_candidate",
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 1
    # The proposal must have been built from the fresh event, not the
    # older consolidated Moment.
    assert (
        "new" in received[0].text.lower()
        or "fresh" in received[0].text.lower()
        or received[0].context.get("moment_id") == "moment_fresh"
    )


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mind_does_not_propose_outside_reflective(
    nats_server, tmp_path: Path
):
    db = tmp_path / "m.db"
    service = MindService(nats_url=nats_server, db_path=db)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[UtteranceProposal] = []

    async def collect(msg: UtteranceProposal) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "mind.utterance_proposal", UtteranceProposal, collect
        )
        await listener.flush()

        async with AegisBus.connect(nats_server) as publisher:
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
            await asyncio.sleep(0.3)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert received == []
