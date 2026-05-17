from aegis_core.services.senses.sources.host_activity_reader import (
    ActivityDecision,
    ActivityReading,
    ActivityThresholds,
    decide,
)


def test_recent_input_is_present_and_engaged():
    decision = decide(
        ActivityReading(idle_seconds=5.0, frontmost_app="Code"),
        ActivityThresholds(),
    )
    assert decision.present is True
    assert decision.engaged is True
    assert decision.frontmost_app == "Code"


def test_idle_past_engaged_cutoff_is_present_not_engaged():
    decision = decide(
        ActivityReading(idle_seconds=120.0, frontmost_app="Code"),
        ActivityThresholds(),
    )
    assert decision.present is True
    assert decision.engaged is False


def test_idle_past_present_cutoff_is_absent():
    decision = decide(
        ActivityReading(idle_seconds=600.0, frontmost_app=None),
        ActivityThresholds(),
    )
    assert decision.present is False
    assert decision.engaged is False


def test_engaged_decision_maps_to_screen_gaze():
    from datetime import UTC, datetime

    from aegis_core.services.senses.sources.host_activity_reader import (
        ActivityDecision,
        to_messages,
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    messages = to_messages(
        ActivityDecision(present=True, engaged=True, frontmost_app="Code"),
        now,
    )
    subjects = [subject for subject, _ in messages]
    assert subjects == ["senses.presence", "senses.posture"]

    presence = messages[0][1]
    posture = messages[1][1]
    assert presence.present is True
    assert presence.source == "host_input"
    assert presence.confidence == 1.0
    assert posture.at_desk is True
    assert posture.gaze == "screen"
    assert posture.movement_score == 1.0


def test_present_not_engaged_maps_to_away_gaze():
    from datetime import UTC, datetime

    from aegis_core.services.senses.sources.host_activity_reader import (
        ActivityDecision,
        to_messages,
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    messages = to_messages(
        ActivityDecision(present=True, engaged=False, frontmost_app="Mail"),
        now,
    )
    posture = messages[1][1]
    assert posture.gaze == "away"
    assert posture.movement_score == 0.0


def test_absent_decision_maps_to_absent_gaze():
    from datetime import UTC, datetime

    from aegis_core.services.senses.sources.host_activity_reader import (
        ActivityDecision,
        to_messages,
    )

    now = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    messages = to_messages(
        ActivityDecision(present=False, engaged=False, frontmost_app=None),
        now,
    )
    presence = messages[0][1]
    posture = messages[1][1]
    assert presence.present is False
    assert posture.at_desk is False
    assert posture.gaze == "absent"
