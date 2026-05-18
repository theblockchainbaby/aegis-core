from datetime import UTC, datetime

import pytest

from aegis_core.messages import (
    AmbientLightReading,
    PostureObserved,
    PresenceObserved,
    ThermalReading,
    VoiceActivityDetected,
)


def test_voice_activity_roundtrip():
    msg = VoiceActivityDetected(
        timestamp=datetime.now(UTC),
        active=True,
        rms_db=-32.0,
        confidence=0.88,
    )
    assert VoiceActivityDetected.model_validate_json(msg.model_dump_json()) == msg


def test_posture_roundtrip():
    msg = PostureObserved(
        timestamp=datetime.now(UTC),
        at_desk=True,
        gaze="screen",
        movement_score=0.05,
    )
    assert PostureObserved.model_validate_json(msg.model_dump_json()) == msg


def test_posture_rejects_unknown_gaze():
    with pytest.raises(ValueError):
        PostureObserved(
            timestamp=datetime.now(UTC),
            at_desk=True,
            gaze="elsewhere",  # not in the literal set
            movement_score=0.0,
        )


def test_ambient_light_roundtrip():
    msg = AmbientLightReading(timestamp=datetime.now(UTC), lux=412.5)
    assert AmbientLightReading.model_validate_json(msg.model_dump_json()) == msg


def test_thermal_roundtrip():
    msg = ThermalReading(timestamp=datetime.now(UTC), celsius=46.2)
    assert ThermalReading.model_validate_json(msg.model_dump_json()) == msg


def test_presence_observed_accepts_host_input_source():
    from datetime import UTC, datetime


    msg = PresenceObserved(
        timestamp=datetime.now(UTC),
        present=True,
        source="host_input",
        confidence=1.0,
    )
    assert msg.source == "host_input"
