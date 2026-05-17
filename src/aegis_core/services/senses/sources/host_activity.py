"""macOS host activity Source for the senses service.

This is the I/O layer. The two reader functions call into Quartz and
AppKit through PyObjC. They read permission free signals only: system
idle time and the frontmost application name. They never read window
titles or keystroke content.

The pure decision logic lives in host_activity_reader.py.
"""
from __future__ import annotations


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
