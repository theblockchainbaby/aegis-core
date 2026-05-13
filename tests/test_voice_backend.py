import io
from pathlib import Path

import pytest

from aegis_core.services.voice.backend import (
    StdoutBackend,
    VoiceBackend,
)


@pytest.mark.asyncio
async def test_stdout_backend_writes_to_stream():
    buf = io.StringIO()
    b = StdoutBackend(stream=buf, log_path=None)
    await b.speak("Yesterday you mentioned the landing page.")
    out = buf.getvalue()
    assert "Yesterday you mentioned the landing page." in out


@pytest.mark.asyncio
async def test_stdout_backend_appends_to_log_file(tmp_path: Path):
    buf = io.StringIO()
    log = tmp_path / "voice.log"
    b = StdoutBackend(stream=buf, log_path=log)
    await b.speak("first line")
    await b.speak("second line")
    text = log.read_text()
    assert "first line" in text
    assert "second line" in text
    assert text.index("first line") < text.index("second line")


def test_backend_satisfies_protocol():
    assert isinstance(StdoutBackend(), VoiceBackend)
