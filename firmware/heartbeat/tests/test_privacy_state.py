import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from privacy_state import STATE_ORDINALS, mic_should_be_powered, palette_name_for_state


def test_ordinal_mapping_complete():
    assert STATE_ORDINALS == {
        "sleep": 0,
        "dormant": 1,
        "observing": 2,
        "attentive": 3,
        "settling": 4,
        "reflective": 5,
        "quiet": 6,
    }


def test_mic_powered_only_when_above_dormant():
    assert mic_should_be_powered("sleep") is False
    assert mic_should_be_powered("dormant") is False
    assert mic_should_be_powered("observing") is True
    assert mic_should_be_powered("attentive") is True
    assert mic_should_be_powered("settling") is True
    assert mic_should_be_powered("reflective") is True
    assert mic_should_be_powered("quiet") is True


def test_palette_name_for_each_state():
    for state in STATE_ORDINALS:
        assert palette_name_for_state(state) == state
