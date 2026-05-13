"""End-to-end test: spin up all nine service stubs, ping each, verify pong."""
import asyncio

import pytest

from aegis_core.bus import AegisBus
from aegis_core.services import (
    observer,
)

ALL_NAMES = [
    "observer",
]

FACTORIES = {
    "observer": observer.make_service,
}


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_all_services_answer_ping(nats_server):
    services = [FACTORIES[n](nats_url=nats_server) for n in ALL_NAMES]
    tasks = [asyncio.create_task(s.run()) for s in services]

    # Wait for setup.
    await asyncio.sleep(0.5)

    replies: dict[str, str] = {}

    async with AegisBus.connect(nats_server) as bus:
        async def collect(raw):
            replies[raw.subject.split(".")[-1]] = raw.data.decode()

        for name in ALL_NAMES:
            await bus._nc.subscribe(f"ping.reply.{name}", cb=collect)
        await bus.flush()

        for name in ALL_NAMES:
            await bus._nc.publish("ping.request", name.encode())
        await bus.flush()

        for _ in range(100):
            if len(replies) == len(ALL_NAMES):
                break
            await asyncio.sleep(0.05)

    for s in services:
        s.shutdown()
    await asyncio.gather(*tasks, return_exceptions=True)

    missing = set(ALL_NAMES) - set(replies)
    assert not missing, f"no reply from: {sorted(missing)}"
    for name in ALL_NAMES:
        assert f"pong from {name}" in replies[name]
