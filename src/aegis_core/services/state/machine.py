"""Presence State Machine — pure logic, no I/O.

Owns the current state, time-in-state, and the transition rules. The state
service in service.py wraps this with NATS plumbing.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ...messages import (
    AmbientLightReading,
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
    VoiceActivityDetected,
)
from .rules import MIN_DWELL_MS, is_allowed

_DARK_LUX_THRESHOLD = 5.0
_DARK_TICKS_FOR_SLEEP = 3


class PresenceStateMachine:
    """In-memory state machine. Drive via observe_*() and tick_ms()."""

    def __init__(self, initial: PresenceState = PresenceState.DORMANT) -> None:
        self._state = initial
        self._dwell_ms = 0
        self._dark_streak = 0
        self._settling_target: PresenceState | None = None

    @property
    def current(self) -> PresenceState:
        return self._state

    @property
    def dwell_ms(self) -> int:
        return self._dwell_ms

    def tick_ms(self, ms: int) -> None:
        """Advance virtual time. Use in tests; the service uses real clock."""
        self._dwell_ms += ms

    def force_state(self, state: PresenceState) -> None:
        """Test-only helper to set state without firing a transition."""
        self._state = state
        self._dwell_ms = 0

    def _make_transition(self, to_state: PresenceState, reason: str) -> StateChanged:
        prev = self._state
        self._state = to_state
        self._dwell_ms = 0
        return StateChanged(
            timestamp=datetime.now(UTC),
            previous=prev,
            current=to_state,
            reason=reason,
        )

    def request_transition(
        self,
        to_state: PresenceState,
        reason: str,
    ) -> StateChanged | None:
        """Attempt a transition. Honors dwell minimums and allowed-edges table.

        If a direct transition isn't allowed but Settling is, route through
        Settling automatically (returns the Settling transition; caller
        re-requests the target after Settling dwell expires).
        """
        if self._dwell_ms < MIN_DWELL_MS[self._state]:
            return None

        if is_allowed(self._state, to_state):
            return self._make_transition(to_state, reason)

        # If we can reach Settling from here, route there first, and
        # remember the target so complete_settling can land correctly.
        if is_allowed(self._state, PresenceState.SETTLING):
            self._settling_target = to_state
            return self._make_transition(PresenceState.SETTLING, f"settling_for:{reason}")

        return None

    def elapse(self) -> StateChanged | None:
        """Called periodically by the service tick. Handles auto-expirations.

        - Quiet → Observing after Quiet dwell.
        - Settling → its target after Settling dwell (target is encoded in
          the prior transition reason; the service tracks it).
        For Plan B we only auto-expire Quiet → Observing here. Settling
        return is handled by the service tracking the requested target.
        """
        if (
            self._state == PresenceState.QUIET
            and self._dwell_ms >= MIN_DWELL_MS[PresenceState.QUIET]
        ):
            return self._make_transition(PresenceState.OBSERVING, "quiet_expired")
        return None

    def complete_settling(self) -> StateChanged | None:
        """Land the organism once the Settling dwell expires.

        Settling is a cushion. When it expires, descend toward Observing if
        the routed target was a lower state (sensor events then carry the
        organism the rest of the way down to Dormant). Otherwise return to
        Attentive. Returns None if not currently Settling or the dwell
        minimum has not yet elapsed.
        """
        if self._state != PresenceState.SETTLING:
            return None
        if self._dwell_ms < MIN_DWELL_MS[PresenceState.SETTLING]:
            return None
        descent = {
            PresenceState.OBSERVING,
            PresenceState.DORMANT,
            PresenceState.SLEEP,
        }
        landing = (
            PresenceState.OBSERVING
            if self._settling_target in descent
            else PresenceState.ATTENTIVE
        )
        self._settling_target = None
        return self._make_transition(landing, "settling_complete")

    # --- event ingestors ---

    def observe_presence(self, msg: PresenceObserved) -> StateChanged | None:
        if msg.present:
            if self._state == PresenceState.DORMANT:
                return self.request_transition(PresenceState.OBSERVING, "presence_detected")
            return None
        else:
            if self._state in (PresenceState.OBSERVING, PresenceState.ATTENTIVE):
                return self.request_transition(PresenceState.DORMANT, "presence_lost")
            return None

    def observe_posture(self, msg: PostureObserved) -> StateChanged | None:
        if msg.at_desk and msg.gaze == "screen":
            if self._state == PresenceState.OBSERVING:
                return self.request_transition(PresenceState.ATTENTIVE, "engagement_detected")
        return None

    def observe_voice(self, msg: VoiceActivityDetected) -> StateChanged | None:
        # Plan B: voice activity informs the steward (later plans). The state
        # machine itself doesn't transition on voice in v1.
        return None

    def observe_ambient_light(self, msg: AmbientLightReading) -> StateChanged | None:
        if msg.lux < _DARK_LUX_THRESHOLD:
            self._dark_streak += 1
        else:
            self._dark_streak = 0
        if (
            self._dark_streak >= _DARK_TICKS_FOR_SLEEP
            and self._state == PresenceState.DORMANT
        ):
            return self.request_transition(PresenceState.SLEEP, "dark_room")
        return None
