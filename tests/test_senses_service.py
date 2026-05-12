import asyncio
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import PresenceObserved
from aegis_core.services.senses.service import SensesService
from aegis_core.services.senses.sources.mock_presence import MockPresenceSource


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_senses_publishes_presence_events(nats_server, tmp_path: Path):
    trace = tmp_path / "trace.json"
    trace.write_text(
        '[{"offset_ms": 0, "present": true, "confidence": 0.9}, '
        '{"offset_ms": 10, "present": false, "confidence": 0.8}]'
    )
    source = MockPresenceSource(trace)

    received: list[PresenceObserved] = []

    async def handler(msg: PresenceObserved) -> None:
        received.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("senses.presence", PresenceObserved, handler)
        await listener.flush()

        service = SensesService(nats_url=nats_server, sources=[source])
        task = asyncio.create_task(service.run())
        for _ in range(50):
            if len(received) == 2:
                break
            await asyncio.sleep(0.05)
        service.shutdown()
        await asyncio.wait_for(task, timeout=5)

    assert len(received) == 2
    assert received[0].present is True
    assert received[1].present is False
