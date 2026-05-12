"""Plan B capstone — feed the canonical-cycle fixture through senses+state.

Honest fixture replay (no synthetic events). TraceRunner paces events at
min_pacing_ms=50 wall clock between events; the StateService runs with
accelerate_for_test=50, so each 50ms wall = 2500ms virtual time. That
comfortably exceeds the 500ms OBSERVING and 1000ms DORMANT dwell minimums
the canonical-cycle trace exercises, so every transition has time to
satisfy Presence Momentum before the next sensor event arrives.
"""
import asyncio
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import PresenceState, StateChanged
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
            sources=[TraceRunner(FIXTURE, real_time=False, min_pacing_ms=50)],
        )

        # state must subscribe to senses.* before senses publishes anything.
        state_task = asyncio.create_task(state_service.run())
        await asyncio.sleep(0.3)
        senses_task = asyncio.create_task(senses_service.run())

        await asyncio.wait([senses_task], timeout=15)
        await asyncio.sleep(0.5)  # let the state machine catch up

        state_service.shutdown()
        senses_service.shutdown()
        await asyncio.gather(state_task, senses_task, return_exceptions=True)

    transitions = [(t.previous, t.current) for t in received]
    expected_subset = [
        (PresenceState.DORMANT, PresenceState.OBSERVING),
        (PresenceState.OBSERVING, PresenceState.ATTENTIVE),
    ]
    for edge in expected_subset:
        assert edge in transitions, f"missing transition {edge}; got {transitions}"
