from datetime import UTC, datetime

import pytest

from aegis_core.messages import (
    PostureObserved,
    PresenceObserved,
    PresenceState,
    VoiceActivityDetected,
)
from aegis_core.services.state.machine import PresenceStateMachine
from aegis_core.services.state.rules import MIN_DWELL_MS


def _now():
    return datetime.now(UTC)


def test_initial_state_is_dormant():
    m = PresenceStateMachine()
    assert m.current == PresenceState.DORMANT


def test_dormant_to_observing_on_presence():
    m = PresenceStateMachine()
    # Need to exit the Dormant min-dwell first.
    m.tick_ms(MIN_DWELL_MS[PresenceState.DORMANT] + 1)
    transition = m.observe_presence(
        PresenceObserved(timestamp=_now(), present=True, source="mmwave", confidence=0.95)
    )
    assert transition is not None
    assert transition.previous == PresenceState.DORMANT
    assert transition.current == PresenceState.OBSERVING


def test_dwell_floor_prevents_transition():
    m = PresenceStateMachine()
    # Don't advance ticks — we're still under the Dormant min dwell.
    transition = m.observe_presence(
        PresenceObserved(timestamp=_now(), present=True, source="mmwave", confidence=0.95)
    )
    assert transition is None
    assert m.current == PresenceState.DORMANT


def test_attentive_to_reflective_requires_settling_then_attentive_first():
    """Reflective may be entered directly from Attentive; leaving must go through Settling."""
    m = PresenceStateMachine()
    m.force_state(PresenceState.ATTENTIVE)
    m.tick_ms(MIN_DWELL_MS[PresenceState.ATTENTIVE] + 1)
    t1 = m.request_transition(PresenceState.REFLECTIVE, reason="memory_candidate")
    assert t1 is not None
    assert m.current == PresenceState.REFLECTIVE
    # Now try to leave Reflective straight back to Attentive — not allowed.
    m.tick_ms(MIN_DWELL_MS[PresenceState.REFLECTIVE] + 1)
    t2 = m.request_transition(PresenceState.ATTENTIVE, reason="reflective_done")
    assert t2 is not None
    assert m.current == PresenceState.SETTLING


def test_observing_quiets_after_ignored_intervention():
    m = PresenceStateMachine()
    m.force_state(PresenceState.OBSERVING)
    m.tick_ms(MIN_DWELL_MS[PresenceState.OBSERVING] + 1)
    t = m.request_transition(PresenceState.QUIET, reason="ignored_intervention")
    assert t is not None
    assert m.current == PresenceState.QUIET


def test_quiet_auto_expires_to_observing_after_dwell():
    m = PresenceStateMachine()
    m.force_state(PresenceState.QUIET)
    m.tick_ms(MIN_DWELL_MS[PresenceState.QUIET] + 1)
    t = m.elapse()
    assert t is not None
    assert t.previous == PresenceState.QUIET
    assert t.current == PresenceState.OBSERVING


from aegis_core.messages import AmbientLightReading


def test_dark_room_in_dormant_eventually_sleeps():
    m = PresenceStateMachine()
    m.force_state(PresenceState.DORMANT)
    m.tick_ms(MIN_DWELL_MS[PresenceState.DORMANT] + 1)

    for _ in range(3):
        t = m.observe_ambient_light(AmbientLightReading(timestamp=_now(), lux=2.0))
    assert m.current == PresenceState.SLEEP


def test_lit_room_does_not_sleep():
    m = PresenceStateMachine()
    m.force_state(PresenceState.DORMANT)
    m.tick_ms(MIN_DWELL_MS[PresenceState.DORMANT] + 1)

    for _ in range(10):
        t = m.observe_ambient_light(AmbientLightReading(timestamp=_now(), lux=400.0))
    assert m.current == PresenceState.DORMANT
