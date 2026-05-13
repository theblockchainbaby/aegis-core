from datetime import UTC, datetime

import pytest

from aegis_core.messages import MoodChanged, Palette


def test_mood_changed_roundtrip():
    msg = MoodChanged(
        timestamp=datetime.now(UTC),
        palette=Palette.ATTENTIVE_WARM,
        breath_cadence_seconds=5.5,
        warmth=0.7,
        reason="state_attentive",
    )
    assert MoodChanged.model_validate_json(msg.model_dump_json()) == msg


def test_mood_changed_rejects_invalid_warmth():
    with pytest.raises(ValueError):
        MoodChanged(
            timestamp=datetime.now(UTC),
            palette=Palette.ATTENTIVE_WARM,
            breath_cadence_seconds=5.0,
            warmth=1.5,
            reason="x",
        )


def test_mood_changed_rejects_negative_cadence():
    with pytest.raises(ValueError):
        MoodChanged(
            timestamp=datetime.now(UTC),
            palette=Palette.ATTENTIVE_WARM,
            breath_cadence_seconds=-1.0,
            warmth=0.5,
            reason="x",
        )


def test_palette_values():
    assert Palette.SLEEP.value == "sleep"
    assert Palette.DORMANT_BLUE.value == "dormant_blue"
    assert Palette.OBSERVING_DRIFT.value == "observing_drift"
    assert Palette.ATTENTIVE_WARM.value == "attentive_warm"
    assert Palette.SETTLING_REGRESS.value == "settling_regress"
    assert Palette.REFLECTIVE_VIOLET.value == "reflective_violet"
    assert Palette.QUIET_COOL.value == "quiet_cool"
