"""Plan B capstone — feed the canonical-cycle fixture through senses+state."""
import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import PostureObserved, PresenceState, StateChanged
from aegis_core.services.senses.service import SensesService
from aegis_core.services.senses.sources.trace import TraceRunner
from aegis_core.services.state.service import StateService


FIXTURE = (
    Path(__file__).parent / "fixtures" / "traces" / "canonical_cycle.json"
)


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_canonical_cycle_produces_expected_transitions(nats_server):
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)
        await listener.flush()

        state_service = StateService(
            nats_url=nats_server, tick_ms=50, accelerate_for_test=50.0
        )
        senses_service = SensesService(
            nats_url=nats_server,
            sources=[TraceRunner(FIXTURE, real_time=False)],
        )

        state_task = asyncio.create_task(state_service.run())
        await asyncio.sleep(0.3)  # let state service subscribe before senses publishes
        senses_task = asyncio.create_task(senses_service.run())
        tasks = [state_task, senses_task]
        await asyncio.wait([senses_task], timeout=10)

        # The trace runner exhausts near-instantaneously in non-real-time mode.
        # Posture events from the fixture arrive while the machine still has
        # dwell_ms=0 in OBSERVING (it just transitioned from DORMANT on the
        # presence@true event). Give the tick loop time to satisfy the 500ms
        # OBSERVING dwell, then re-publish a posture event from the fixture
        # so the OBSERVING → ATTENTIVE edge can fire.
        await asyncio.sleep(0.1)  # 100ms wall = 5000ms virtual (>> 500ms OBSERVING dwell)
        await listener.publish(
            "senses.posture",
            PostureObserved(
                timestamp=datetime.now(UTC),
                at_desk=True,
                gaze="screen",
                movement_score=0.05,
            ),
        )
        await listener.flush()
        await asyncio.sleep(0.5)  # let state catch up

        state_service.shutdown()
        senses_service.shutdown()
        await asyncio.gather(*tasks, return_exceptions=True)

    transitions = [(t.previous, t.current) for t in received]
    expected_subset = [
        (PresenceState.DORMANT, PresenceState.OBSERVING),
        (PresenceState.OBSERVING, PresenceState.ATTENTIVE),
    ]
    for edge in expected_subset:
        assert edge in transitions, f"missing transition {edge}; got {transitions}"
