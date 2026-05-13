from aegis_core.messages import Palette, PresenceState
from aegis_core.services.mood.inference import MoodSignals, infer_mood


def test_dormant_to_dormant_blue():
    m = infer_mood(state=PresenceState.DORMANT, signals=MoodSignals())
    assert m.palette == Palette.DORMANT_BLUE
    assert m.breath_cadence_seconds > 6.0  # slow
    assert m.warmth < 0.2


def test_attentive_to_attentive_warm():
    m = infer_mood(state=PresenceState.ATTENTIVE, signals=MoodSignals())
    assert m.palette == Palette.ATTENTIVE_WARM
    assert 4.0 <= m.breath_cadence_seconds <= 6.5
    assert m.warmth > 0.5


def test_reflective_to_reflective_violet():
    m = infer_mood(state=PresenceState.REFLECTIVE, signals=MoodSignals())
    assert m.palette == Palette.REFLECTIVE_VIOLET


def test_sleep_to_sleep_palette():
    m = infer_mood(state=PresenceState.SLEEP, signals=MoodSignals())
    assert m.palette == Palette.SLEEP
    assert m.breath_cadence_seconds >= 10.0


def test_quiet_to_quiet_cool():
    m = infer_mood(state=PresenceState.QUIET, signals=MoodSignals())
    assert m.palette == Palette.QUIET_COOL
    assert m.warmth < 0.3


def test_settling_to_settling_regress():
    m = infer_mood(state=PresenceState.SETTLING, signals=MoodSignals())
    assert m.palette == Palette.SETTLING_REGRESS


def test_observing_to_observing_drift():
    m = infer_mood(state=PresenceState.OBSERVING, signals=MoodSignals())
    assert m.palette == Palette.OBSERVING_DRIFT


def test_high_focus_score_warms_attentive_palette():
    base = infer_mood(state=PresenceState.ATTENTIVE, signals=MoodSignals())
    deep = infer_mood(
        state=PresenceState.ATTENTIVE,
        signals=MoodSignals(focus_score=0.95),
    )
    assert deep.warmth >= base.warmth
    assert deep.breath_cadence_seconds >= base.breath_cadence_seconds
