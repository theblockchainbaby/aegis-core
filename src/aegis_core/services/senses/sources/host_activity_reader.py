"""Pure decision logic for the macOS host activity sensor.

No macOS calls and no I/O. Takes a reading of how long the machine has
been idle plus the frontmost app, and decides whether York is present
and whether he is actively engaged. Fully testable on any platform.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityThresholds:
    """Idle time cutoffs, in seconds.

    engaged_idle_seconds: idle shorter than this means actively engaged.
    present_idle_seconds: idle longer than this means York stepped away.
    """

    engaged_idle_seconds: float = 45.0
    present_idle_seconds: float = 300.0


@dataclass(frozen=True)
class ActivityReading:
    """One poll of the host: idle seconds plus the frontmost app name."""

    idle_seconds: float
    frontmost_app: str | None


@dataclass(frozen=True)
class ActivityDecision:
    """Derived presence and engagement for one reading."""

    present: bool
    engaged: bool
    frontmost_app: str | None


def decide(
    reading: ActivityReading, thresholds: ActivityThresholds
) -> ActivityDecision:
    """Map a reading to a presence and engagement decision.

    A reading idle longer than present_idle_seconds is treated as York
    having stepped away. engaged is always a stricter condition than
    present, so an engaged decision always carries present True.
    """
    present = reading.idle_seconds < thresholds.present_idle_seconds
    engaged = reading.idle_seconds < thresholds.engaged_idle_seconds
    return ActivityDecision(
        present=present,
        engaged=engaged,
        frontmost_app=reading.frontmost_app,
    )
