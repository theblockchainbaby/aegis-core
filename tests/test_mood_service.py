import asyncio
from datetime import UTC, datetime

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    MoodChanged,
    Palette,
    PresenceState,
    StateChanged,
)
from aegis_core.services.mood.service import MoodService


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mood_emits_on_state_changed(nats_server):
    service = MoodService(nats_url=nats_server)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[MoodChanged] = []

    async def collect(msg: MoodChanged) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("mood.changed", MoodChanged, collect)
        await listener.flush()

        async with AegisBus.connect(nats_server) as publisher:
            await publisher.publish(
                "state.changed",
                StateChanged(
                    timestamp=datetime.now(UTC),
                    previous=PresenceState.DORMANT,
                    current=PresenceState.ATTENTIVE,
                    reason="engagement",
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.3)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 1
    assert received[0].palette == Palette.ATTENTIVE_WARM
    assert received[0].warmth > 0.5
