from datetime import UTC, datetime

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import PresenceObserved


@pytest.mark.asyncio
async def test_publish_subscribe_roundtrip(nats_server):
    received: list[PresenceObserved] = []

    async def handler(msg: PresenceObserved) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as bus:
        await bus.subscribe("senses.presence", PresenceObserved, handler)
        await bus.publish(
            "senses.presence",
            PresenceObserved(
                timestamp=datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC),
                present=True,
                source="mmwave",
                confidence=0.9,
            ),
        )
        # Give the broker a tick to deliver.
        await bus.flush()
        # Wait briefly for handler.
        import asyncio

        for _ in range(50):
            if received:
                break
            await asyncio.sleep(0.02)

    assert len(received) == 1
    assert received[0].present is True
    assert received[0].source == "mmwave"


@pytest.mark.asyncio
async def test_subscribe_rejects_wrong_schema(nats_server):
    received: list = []

    async def handler(msg: PresenceObserved) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as bus:
        await bus.subscribe("senses.presence", PresenceObserved, handler)
        # Publish malformed JSON via the raw client.
        await bus._nc.publish("senses.presence", b'{"not": "valid"}')
        await bus.flush()
        import asyncio

        await asyncio.sleep(0.2)

    assert received == []  # handler never invoked on malformed payload
