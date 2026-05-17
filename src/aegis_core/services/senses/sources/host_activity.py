"""macOS host activity Source for the senses service.

This is the I/O layer. The two reader functions call into Quartz and
AppKit through PyObjC. They read permission free signals only: system
idle time and the frontmost application name. They never read window
titles or keystroke content.

The pure decision logic lives in host_activity_reader.py.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

from ....messages._base import AegisMessage
from .host_activity_reader import (
    ActivityReading,
    ActivityThresholds,
    decide,
    to_messages,
)


def read_idle_seconds() -> float:
    """Seconds since the last keyboard or mouse event, system wide.

    Uses Quartz CGEventSourceSecondsSinceLastEventType. This call does
    not require Accessibility or Input Monitoring permission.
    """
    from Quartz import (
        CGEventSourceSecondsSinceLastEventType,
        kCGAnyInputEventType,
        kCGEventSourceStateHIDSystemState,
    )

    return float(
        CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
        )
    )


def read_frontmost_app() -> str | None:
    """Localized name of the frontmost application, or None.

    Uses AppKit NSWorkspace. This call does not require any permission.
    Returns the application name only, never the window title.
    """
    from AppKit import NSWorkspace

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None
    name = app.localizedName()
    return str(name) if name is not None else None


class HostActivitySource:
    """Senses Source that polls macOS host activity on a fixed cadence.

    Each poll reads idle seconds and the frontmost app, runs the pure
    decision logic, and yields a PresenceObserved followed by a
    PostureObserved. The two reader callables default to the real macOS
    functions and are injectable so the loop can be tested anywhere.
    """

    name = "host_activity"

    def __init__(
        self,
        poll_interval_seconds: float = 5.0,
        thresholds: ActivityThresholds | None = None,
        idle_reader: Callable[[], float] = read_idle_seconds,
        app_reader: Callable[[], str | None] = read_frontmost_app,
    ) -> None:
        self._poll = poll_interval_seconds
        self._thresholds = thresholds or ActivityThresholds()
        self._idle_reader = idle_reader
        self._app_reader = app_reader
        self._closed = False

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        while not self._closed:
            reading = ActivityReading(
                idle_seconds=self._idle_reader(),
                frontmost_app=self._app_reader(),
            )
            decision = decide(reading, self._thresholds)
            for subject, msg in to_messages(decision, datetime.now(UTC)):
                yield subject, msg
            await asyncio.sleep(self._poll)

    async def aclose(self) -> None:
        self._closed = True
