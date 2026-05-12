import asyncio
from datetime import UTC, datetime

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
)
from aegis_core.services.state.service import StateService


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_state_service_transitions_on_presence_and_engagement(nats_server):
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)
        await listener.flush()

        service = StateService(nats_url=nats_server, tick_ms=100, accelerate_for_test=10)
        task = asyncio.create_task(service.run())
        await asyncio.sleep(0.3)

        async with AegisBus.connect(nats_server) as publisher:
            # Need to wait past Dormant dwell. With accelerate_for_test=10,
            # 1000ms of in-machine time happens in 100ms of wall-clock.
            await asyncio.sleep(0.2)
            await publisher.publish(
                "senses.presence",
                PresenceObserved(
                    timestamp=datetime.now(UTC),
                    present=True,
                    source="mmwave",
                    confidence=0.95,
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.3)

            # Now post a posture event to push from Observing → Attentive.
            await publisher.publish(
                "senses.posture",
                PostureObserved(
                    timestamp=datetime.now(UTC),
                    at_desk=True,
                    gaze="screen",
                    movement_score=0.1,
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.3)

        service.shutdown()
        await asyncio.wait_for(task, timeout=5)

    transitions = [(m.previous, m.current) for m in received]
    assert (PresenceState.DORMANT, PresenceState.OBSERVING) in transitions
    assert (PresenceState.OBSERVING, PresenceState.ATTENTIVE) in transitions
