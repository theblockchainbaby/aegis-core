"""Settling descent capstone.

A HostActivitySource with its idle reader pinned to a long idle value
feeds the senses service, which feeds the state machine. The organism
starts ATTENTIVE. It must descend to DORMANT and rest there, never
bouncing back up to ATTENTIVE.

Before the settling fix this thrashed: every poll kicked ATTENTIVE into
SETTLING, and SETTLING bounced straight back to ATTENTIVE, forever. This
test is the regression guard for that bug.
"""
import asyncio

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import PresenceState, StateChanged
from aegis_core.services.senses.service import SensesService
from aegis_core.services.senses.sources.host_activity import HostActivitySource
from aegis_core.services.state.service import StateService


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_organism_descends_and_rests_when_away(nats_server):
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    # Idle pinned far past the present threshold: York is away.
    source = HostActivitySource(
        poll_interval_seconds=0.05,
        idle_reader=lambda: 600.0,
        app_reader=lambda: None,
    )

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)
        await listener.flush()

        state_service = StateService(
            nats_url=nats_server, tick_ms=50, accelerate_for_test=50.0
        )
        state_service._machine.force_state(PresenceState.ATTENTIVE)
        state_service._machine.tick_ms(5_000)  # clear the ATTENTIVE dwell
        senses_service = SensesService(nats_url=nats_server, sources=[source])

        state_task = asyncio.create_task(state_service.run())
        await asyncio.sleep(0.3)
        senses_task = asyncio.create_task(senses_service.run())

        # Let the away stream run long enough to descend and then rest.
        await asyncio.sleep(2.0)

        senses_service.shutdown()
        state_service.shutdown()
        await asyncio.gather(senses_task, state_task, return_exceptions=True)

    currents = [m.current for m in received]
    assert PresenceState.DORMANT in currents, (
        f"organism never reached DORMANT; got {currents}"
    )
    # No thrash: once DORMANT is reached it must not climb back to ATTENTIVE.
    first_dormant = currents.index(PresenceState.DORMANT)
    after = currents[first_dormant + 1:]
    assert PresenceState.ATTENTIVE not in after, (
        f"organism thrashed back up after resting; got {currents}"
    )
    # The descent is a handful of transitions, not relentless oscillation.
    assert len(received) <= 8, (
        f"too many transitions, organism is thrashing; got {currents}"
    )
