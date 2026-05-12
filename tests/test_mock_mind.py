import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from aegis_core.services.mind.mock_mind import MockMindService, ProposalRecipe


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mock_mind_emits_on_reflective(nats_server):
    recipe = ProposalRecipe(
        text="Yesterday you mentioned the landing page.",
        intervention_class=InterventionClass.MEMORY_MAGIC,
        weight=1.0,
        confidence=0.92,
    )
    service = MockMindService(nats_url=nats_server, recipes=[recipe])
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
                    previous=PresenceState.ATTENTIVE,
                    current=PresenceState.REFLECTIVE,
                    reason="t",
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 1
    assert received[0].text == "Yesterday you mentioned the landing page."


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_mock_mind_cycles_through_recipes(nats_server):
    recipes = [
        ProposalRecipe(
            text=f"line {i}",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.9,
        )
        for i in range(3)
    ]
    service = MockMindService(nats_url=nats_server, recipes=recipes)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    received: list[UtteranceProposal] = []

    async def collect(msg: UtteranceProposal) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe(
            "mind.utterance_proposal", UtteranceProposal, collect
        )

        async with AegisBus.connect(nats_server) as publisher:
            for _ in range(5):
                await publisher.publish(
                    "state.changed",
                    StateChanged(
                        timestamp=datetime.now(UTC),
                        previous=PresenceState.ATTENTIVE,
                        current=PresenceState.REFLECTIVE,
                        reason="t",
                    ),
                )
                await publisher.flush()
                await asyncio.sleep(0.1)

            await asyncio.sleep(0.3)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(received) == 5
    # Round-robin through 3 recipes.
    assert [r.text for r in received] == [
        "line 0", "line 1", "line 2", "line 0", "line 1",
    ]
