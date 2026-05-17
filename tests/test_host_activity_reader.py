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
