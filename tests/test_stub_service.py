import asyncio

import pytest

from aegis_core.bus import AegisBus
from aegis_core.services._stub import StubService


@pytest.mark.asyncio
async def test_stub_service_responds_to_ping(nats_server):
    service = StubService(name="senses", nats_url=nats_server)
    task = asyncio.create_task(service.run())

    # Wait for the service to subscribe.
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as bus:
        replies: list[bytes] = []

        async def collect(raw):
            replies.append(raw.data)

        await bus._nc.subscribe("ping.reply.senses", cb=collect)
        await bus._nc.publish("ping.request", b"senses")
        await bus.flush()
        for _ in range(50):
            if replies:
                break
            await asyncio.sleep(0.02)

    service.shutdown()
    await task

    assert len(replies) == 1
    assert b"pong" in replies[0]
