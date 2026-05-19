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


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_state_service_completes_settling_to_attentive(nats_server):
    """After Reflective → Settling, service should advance to Attentive once dwell expires."""
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)

        service = StateService(nats_url=nats_server, tick_ms=50, accelerate_for_test=20)
        # Force into Attentive after construction (Plan B test convenience).
        service._machine.force_state(PresenceState.ATTENTIVE)
        # Allow Attentive dwell to lapse.
        service._machine.tick_ms(5_000)

        task = asyncio.create_task(service.run())
        await asyncio.sleep(0.2)

        async with AegisBus.connect(nats_server) as publisher:
            # Trigger Reflective (Plan B has no real trigger; use a posture
            # nudge — but our PSM doesn't go to Reflective on posture. So in
            # this test we use request_transition directly via the machine.)
            service._machine.request_transition(PresenceState.REFLECTIVE, "test_reflective")
            await asyncio.sleep(0.2)
            service._machine.request_transition(PresenceState.ATTENTIVE, "test_settle")
            await asyncio.sleep(0.5)
        service.shutdown()
        await asyncio.wait_for(task, timeout=5)

    transitions = [(m.previous, m.current) for m in received]
    # Expect the service to auto-leave Settling (i.e. emit a SETTLING → X transition).
    assert any(prev == PresenceState.SETTLING for prev, _ in transitions), transitions


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_state_service_descends_to_dormant_when_presence_lost(nats_server):
    """A stream of present=False readings must carry the organism down to
    DORMANT, not bounce it back to ATTENTIVE. This is the settling fix."""
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)

        service = StateService(nats_url=nats_server, tick_ms=50, accelerate_for_test=20)
        service._machine.force_state(PresenceState.ATTENTIVE)
        service._machine.tick_ms(5_000)  # clear the ATTENTIVE dwell minimum

        task = asyncio.create_task(service.run())
        await asyncio.sleep(0.2)

        async with AegisBus.connect(nats_server) as publisher:
            for _ in range(12):
                await publisher.publish(
                    "senses.presence",
                    PresenceObserved(
                        timestamp=datetime.now(UTC),
                        present=False,
                        source="host_input",
                        confidence=1.0,
                    ),
                )
                await asyncio.sleep(0.15)

        service.shutdown()
        await asyncio.wait_for(task, timeout=5)

    currents = [m.current for m in received]
    assert PresenceState.DORMANT in currents, (
        f"organism never reached DORMANT; transitions were {currents}"
    )
