"""Tests for the mock sensor sources."""
from pathlib import Path

import pytest

from aegis_core.services.senses.sources.mock_camera import MockCameraSource


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "camera_frames"


@pytest.mark.asyncio
async def test_mock_camera_yields_one_event_per_frame():
    src = MockCameraSource(FIXTURE_DIR)
    events = []
    async for subject, msg in src.events():
        events.append((subject, msg))
    await src.aclose()

    assert len(events) == 3
    subjects = {s for s, _ in events}
    assert subjects == {"senses.posture"}


@pytest.mark.asyncio
async def test_mock_camera_uses_sidecar_metadata():
    src = MockCameraSource(FIXTURE_DIR)
    events = []
    async for _, msg in src.events():
        events.append(msg)
    await src.aclose()

    assert events[0].at_desk is False
    assert events[0].gaze == "absent"
    assert events[1].at_desk is True
    assert events[1].gaze == "screen"
    assert events[1].movement_score == pytest.approx(0.12)
