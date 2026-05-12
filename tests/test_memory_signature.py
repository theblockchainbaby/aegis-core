from datetime import UTC, datetime

from aegis_core.messages import (
    PostureObserved,
    PresenceObserved,
    VoiceActivityDetected,
)
from aegis_core.services.memory.signature import SignatureAccumulator


def _now():
    return datetime.now(UTC)


def test_empty_signature_has_zero_counts():
    sig = SignatureAccumulator().snapshot()
    assert sig["posture_events"] == 0
    assert sig["voice_events"] == 0
    assert sig["presence_events"] == 0
    assert sig["focus_score"] == 0.0
    assert sig["movement_score"] == 0.0


def test_posture_contributes_to_focus_and_movement():
    acc = SignatureAccumulator()
    acc.add_posture(
        PostureObserved(
            timestamp=_now(),
            at_desk=True,
            gaze="screen",
            movement_score=0.05,
        )
    )
    acc.add_posture(
        PostureObserved(
            timestamp=_now(),
            at_desk=True,
            gaze="screen",
            movement_score=0.03,
        )
    )
    sig = acc.snapshot()
    assert sig["posture_events"] == 2
    # Two at_desk+screen frames → focus_score should be > 0.
    assert sig["focus_score"] > 0.0
    # Movement is the mean of the two movement_score values.
    assert abs(sig["movement_score"] - 0.04) < 1e-6


def test_voice_event_active_increments_voice_events():
    acc = SignatureAccumulator()
    acc.add_voice(
        VoiceActivityDetected(
            timestamp=_now(),
            active=True,
            rms_db=-20.0,
            confidence=0.9,
        )
    )
    acc.add_voice(
        VoiceActivityDetected(
            timestamp=_now(),
            active=False,
            rms_db=-40.0,
            confidence=0.7,
        )
    )
    sig = acc.snapshot()
    # Only 'active=True' events count.
    assert sig["voice_events"] == 1


def test_presence_loss_counts_separately():
    acc = SignatureAccumulator()
    acc.add_presence(
        PresenceObserved(
            timestamp=_now(),
            present=False,
            source="mmwave",
            confidence=0.9,
        )
    )
    sig = acc.snapshot()
    assert sig["presence_events"] == 1
    assert sig["presence_lost"] == 1
