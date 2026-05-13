import asyncio
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import InterventionClass, VoiceSpeak
from aegis_core.services.voice.backend import StdoutBackend
from aegis_core.services.voice.service import VoiceService


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_voice_service_renders_voice_speak(nats_server, tmp_path: Path):
    buf = io.StringIO()
    log = tmp_path / "voice.log"
    backend = StdoutBackend(stream=buf, log_path=log)

    service = VoiceService(nats_url=nats_server, backend=backend)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as publisher:
        await publisher.publish(
            "voice.speak",
            VoiceSpeak(
                timestamp=datetime.now(UTC),
                text="Yesterday you mentioned the landing page.",
                intervention_class=InterventionClass.MEMORY_MAGIC,
                weight=1.0,
            ),
        )
        await publisher.flush()
        await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert "Yesterday you mentioned the landing page." in buf.getvalue()
    assert "Yesterday you mentioned the landing page." in log.read_text()
