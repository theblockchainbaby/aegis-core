from datetime import UTC, datetime

import pytest

from aegis_core.messages.sense_events import PresenceObserved
from aegis_core.messages.state_events import PresenceState, StateChanged


def test_presence_observed_roundtrip():
    msg = PresenceObserved(
        timestamp=datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC),
        present=True,
        source="mmwave",
        confidence=0.92,
    )
    raw = msg.model_dump_json()
    restored = PresenceObserved.model_validate_json(raw)
    assert restored == msg


def test_state_changed_validates_known_states():
    for state in PresenceState:
        msg = StateChanged(
            timestamp=datetime.now(UTC),
            previous=PresenceState.DORMANT,
            current=state,
            reason="test",
        )
        assert msg.current == state


def test_state_changed_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        PresenceObserved(
            timestamp=datetime.now(UTC),
            present=True,
            source="mmwave",
            confidence=1.5,  # out of range
        )
