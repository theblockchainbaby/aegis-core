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


from aegis_core.services.senses.sources.mock_audio import MockAudioSource


AUDIO_DIR = Path(__file__).parent / "fixtures" / "audio"


@pytest.mark.asyncio
async def test_mock_audio_detects_quiet_typing_as_inactive():
    src = MockAudioSource(AUDIO_DIR / "attentive_typing.wav")
    events = [msg async for _, msg in src.events()]
    await src.aclose()

    active_fraction = sum(1 for e in events if e.active) / len(events)
    assert active_fraction < 0.1, "near-silence should rarely register as active"


@pytest.mark.asyncio
async def test_mock_audio_detects_sine_burst_as_active():
    src = MockAudioSource(AUDIO_DIR / "spoken_utterance.wav")
    events = [msg async for _, msg in src.events()]
    await src.aclose()

    active_fraction = sum(1 for e in events if e.active) / len(events)
    # The 2-second sine sits within a 3-second file → ~66% active expected.
    assert 0.5 < active_fraction < 0.85


import json
import tempfile

from aegis_core.services.senses.sources.mock_presence import MockPresenceSource


@pytest.mark.asyncio
async def test_mock_presence_replays_recorded_events():
    trace = [
        {"offset_ms": 0, "present": False, "confidence": 0.95},
        {"offset_ms": 500, "present": True, "confidence": 0.97},
        {"offset_ms": 1500, "present": True, "confidence": 0.92},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(trace, f)
        path = f.name

    src = MockPresenceSource(path)
    events = [msg async for _, msg in src.events()]
    await src.aclose()

    assert len(events) == 3
    assert events[0].present is False
    assert events[1].present is True
    assert events[1].source == "mmwave"


from aegis_core.services.senses.sources.mock_environment import MockEnvironmentSource


@pytest.mark.asyncio
async def test_mock_environment_yields_both_readings():
    src = MockEnvironmentSource(lux=200.0, celsius=42.0, ticks=3)
    seen_subjects = set()
    events = []
    async for subject, msg in src.events():
        seen_subjects.add(subject)
        events.append(msg)
    await src.aclose()

    assert seen_subjects == {"senses.ambient_light", "senses.thermal"}
    assert len(events) == 6  # 3 ticks × 2 readings each


TRACE_FILE = Path(__file__).parent / "fixtures" / "traces" / "canonical_cycle.json"


@pytest.mark.asyncio
async def test_trace_runner_yields_events_in_offset_order():
    from aegis_core.services.senses.sources.trace import TraceRunner

    src = TraceRunner(TRACE_FILE)
    events = [evt async for evt in src.events()]
    await src.aclose()

    subjects = [s for s, _ in events]
    assert "senses.presence" in subjects
    assert "senses.posture" in subjects
    assert "senses.voice_activity" in subjects
    # First two events should be presence (offset_ms 0 and 2000).
    assert subjects[0] == "senses.presence"
