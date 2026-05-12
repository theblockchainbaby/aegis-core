"""Presence State Machine — pure logic, no I/O.

Owns the current state, time-in-state, and the transition rules. The state
service in service.py wraps this with NATS plumbing.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from ...messages import (
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
    VoiceActivityDetected,
)
from .rules import ALLOWED_DIRECT, MIN_DWELL_MS, is_allowed


class PresenceStateMachine:
    """In-memory state machine. Drive via observe_*() and tick_ms()."""

    def __init__(self, initial: PresenceState = PresenceState.DORMANT) -> None:
        self._state = initial
        self._dwell_ms = 0

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
    ) -> Optional[StateChanged]:
        """Attempt a transition. Honors dwell minimums and allowed-edges table.

        If a direct transition isn't allowed but Settling is, route through
        Settling automatically (returns the Settling transition; caller
        re-requests the target after Settling dwell expires).
        """
        if self._dwell_ms < MIN_DWELL_MS[self._state]:
            return None

        if is_allowed(self._state, to_state):
            return self._make_transition(to_state, reason)

        # If we can reach Settling from here, route there first.
        if is_allowed(self._state, PresenceState.SETTLING):
            return self._make_transition(PresenceState.SETTLING, f"settling_for:{reason}")

        return None

    def elapse(self) -> Optional[StateChanged]:
        """Called periodically by the service tick. Handles auto-expirations.

        - Quiet → Observing after Quiet dwell.
        - Settling → its target after Settling dwell (target is encoded in
          the prior transition reason; the service tracks it).
        For Plan B we only auto-expire Quiet → Observing here. Settling
        return is handled by the service tracking the requested target.
        """
        if self._state == PresenceState.QUIET and self._dwell_ms >= MIN_DWELL_MS[PresenceState.QUIET]:
            return self._make_transition(PresenceState.OBSERVING, "quiet_expired")
        return None

    # --- event ingestors ---

    def observe_presence(self, msg: PresenceObserved) -> Optional[StateChanged]:
        if msg.present:
            if self._state == PresenceState.DORMANT:
                return self.request_transition(PresenceState.OBSERVING, "presence_detected")
            return None
        else:
            if self._state in (PresenceState.OBSERVING, PresenceState.ATTENTIVE):
                return self.request_transition(PresenceState.DORMANT, "presence_lost")
            return None

    def observe_posture(self, msg: PostureObserved) -> Optional[StateChanged]:
        if msg.at_desk and msg.gaze == "screen":
            if self._state == PresenceState.OBSERVING:
                return self.request_transition(PresenceState.ATTENTIVE, "engagement_detected")
        return None

    def observe_voice(self, msg: VoiceActivityDetected) -> Optional[StateChanged]:
        # Plan B: voice activity informs the steward (later plans). The state
        # machine itself doesn't transition on voice in v1.
        return None
