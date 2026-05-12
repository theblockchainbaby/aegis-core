"""Social Recovery — short-arc state machine.

Spec §6 social_recovery: after an unacknowledged utterance, the Steward
becomes temporarily quieter. Per the design principles, this models how
humans pull back after an awkward interaction. Deterministic; tests can
drive it via FakeClock.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .clock import Clock


class SocialRecovery:
    def __init__(
        self,
        clock: Clock,
        timeout_seconds: float,
        confidence_bump: float,
        cooldown_minutes: float,
    ) -> None:
        self._clock = clock
        self._timeout = timedelta(seconds=timeout_seconds)
        self._bump = confidence_bump
        self._cooldown = timedelta(minutes=cooldown_minutes)

        self._outstanding_at: datetime | None = None
        self._outstanding_class: str | None = None
        self._cooldown_until: datetime | None = None

    def note_utterance(self, class_: str) -> None:
        self._outstanding_at = self._clock.now()
        self._outstanding_class = class_

    def note_acknowledgment(self) -> None:
        self._outstanding_at = None
        self._outstanding_class = None

    def tick(self) -> None:
        now = self._clock.now()
        # Engage recovery if outstanding utterance exceeded timeout.
        if (
            self._outstanding_at is not None
            and (now - self._outstanding_at) >= self._timeout
        ):
            self._cooldown_until = now + self._cooldown
            self._outstanding_at = None
            self._outstanding_class = None
        # Expire cooldown.
        if self._cooldown_until is not None and now >= self._cooldown_until:
            self._cooldown_until = None

    def is_active(self) -> bool:
        if self._cooldown_until is None:
            return False
        return self._clock.now() < self._cooldown_until

    def threshold_bump(self) -> float:
        return self._bump if self.is_active() else 0.0
