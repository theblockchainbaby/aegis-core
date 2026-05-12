"""Presence Decay — long-arc adaptive silence pacing.

Spec §6 presence_decay: low engagement over a rolling window scales the
silence budget down (and the per-utterance weight cost up). Plan D ships
the math + a manual tick() driven by the service's daily/weekly cron;
the floor prevents the Node from going fully silent.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .clock import Clock


class PresenceDecay:
    def __init__(
        self,
        clock: Clock,
        window_days: int,
        low_engagement_threshold_per_week: int,
        multiplier_per_step: float,
        floor: float,
        baseline_budget: float,
    ) -> None:
        self._clock = clock
        self._window = timedelta(days=window_days)
        self._threshold = low_engagement_threshold_per_week
        self._multiplier_step = multiplier_per_step
        self._floor = floor
        self._baseline = baseline_budget

        self._multiplier = 1.0
        self._last_tick_at: datetime | None = None

    def multiplier(self) -> float:
        return self._multiplier

    def effective_budget(self) -> float:
        return max(self._floor, self._baseline / self._multiplier)

    def tick(self, acknowledged_this_window: int) -> None:
        now = self._clock.now()
        if (
            self._last_tick_at is not None
            and (now - self._last_tick_at) < self._window
        ):
            return  # don't tick within a window
        self._last_tick_at = now

        if acknowledged_this_window < self._threshold:
            # Low engagement — apply one step of decay (up to floor).
            candidate = self._multiplier * self._multiplier_step
            # Clamp so effective_budget never falls below floor.
            max_mult = self._baseline / self._floor
            self._multiplier = min(candidate, max_mult)
        else:
            # Engaged — reset.
            self._multiplier = 1.0
