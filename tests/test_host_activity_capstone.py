"""Host activity capstone.

A HostActivitySource with an injected idle reader feeds the senses
service. The state service runs with an accelerated clock, the same
technique the Plan B capstone uses, so the dwell minimums (500ms for
OBSERVING, 1000ms for ATTENTIVE) are satisfied between polls.

Proves the awakening path: host activity moves the organism from
DORMANT to OBSERVING to ATTENTIVE. This is the dogfood unblock.
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
async def test_host_activity_drives_organism_awake(nats_server):
    received: list[StateChanged] = []

    async def collect(msg: StateChanged) -> None:
        received.append(msg)

    source = HostActivitySource(
        poll_interval_seconds=0.05,
        idle_reader=lambda: 5.0,
        app_reader=lambda: "Code",
    )

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("state.changed", StateChanged, collect)
        await listener.flush()

        state_service = StateService(
            nats_url=nats_server, tick_ms=50, accelerate_for_test=50.0
        )
        senses_service = SensesService(
            nats_url=nats_server, sources=[source]
        )

        state_task = asyncio.create_task(state_service.run())
        await asyncio.sleep(0.3)
        senses_task = asyncio.create_task(senses_service.run())

        transitions: list[tuple[PresenceState, PresenceState]] = []
        for _ in range(200):
            transitions = [(t.previous, t.current) for t in received]
            currents = [current for _, current in transitions]
            if (
                PresenceState.OBSERVING in currents
                and PresenceState.ATTENTIVE in currents
            ):
                break
            await asyncio.sleep(0.05)

        senses_service.shutdown()
        state_service.shutdown()
        await asyncio.gather(
            senses_task, state_task, return_exceptions=True
        )

    currents = [current for _, current in transitions]
    assert PresenceState.OBSERVING in currents, (
        f"organism never reached OBSERVING; got {transitions}"
    )
    assert PresenceState.ATTENTIVE in currents, (
        f"organism never reached ATTENTIVE; got {transitions}"
    )
