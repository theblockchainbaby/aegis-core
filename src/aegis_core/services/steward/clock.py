"""Clock — pluggable for deterministic tests.

Same shape as Brain Reverie's host-compat shim, lifted into a Protocol so
multiple services (Steward, future Mood) can share the pattern.
"""
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock:
    """Test-only clock with an explicit advance() method."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock requires a timezone-aware start datetime")
        self._now = start
        self._mono = 0.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> None:
        from datetime import timedelta as _td

        self._now = self._now + _td(seconds=seconds)
        self._mono = self._mono + seconds
