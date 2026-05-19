from datetime import UTC, datetime

from aegis_core.messages import (
    PresenceObserved,
    PresenceState,
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


def test_complete_settling_descent_target_lands_on_observing():
    m = PresenceStateMachine(initial=PresenceState.ATTENTIVE)
    m.tick_ms(5_000)  # clear the ATTENTIVE dwell minimum
    routed = m.request_transition(PresenceState.DORMANT, "presence_lost")
    assert routed is not None
    assert m.current == PresenceState.SETTLING
    m.tick_ms(5_000)  # clear the SETTLING dwell minimum
    done = m.complete_settling()
    assert done is not None
    assert done.current == PresenceState.OBSERVING
    assert done.reason == "settling_complete"
    assert m.current == PresenceState.OBSERVING


def test_complete_settling_upward_target_lands_on_attentive():
    m = PresenceStateMachine(initial=PresenceState.REFLECTIVE)
    m.tick_ms(5_000)  # clear the REFLECTIVE dwell minimum
    routed = m.request_transition(PresenceState.ATTENTIVE, "leaving_reflective")
    assert routed is not None
    assert m.current == PresenceState.SETTLING
    m.tick_ms(5_000)  # clear the SETTLING dwell minimum
    done = m.complete_settling()
    assert done is not None
    assert done.current == PresenceState.ATTENTIVE
    assert m.current == PresenceState.ATTENTIVE


def test_complete_settling_noop_when_not_settling():
    m = PresenceStateMachine(initial=PresenceState.ATTENTIVE)
    assert m.complete_settling() is None


def test_complete_settling_waits_for_settling_dwell():
    m = PresenceStateMachine(initial=PresenceState.ATTENTIVE)
    m.tick_ms(5_000)
    m.request_transition(PresenceState.DORMANT, "presence_lost")
    assert m.current == PresenceState.SETTLING
    # The SETTLING dwell minimum has not elapsed yet, so completion holds.
    assert m.complete_settling() is None
