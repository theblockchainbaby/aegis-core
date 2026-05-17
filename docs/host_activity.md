# Host Activity Sensor

Read this before touching `src/aegis_core/services/senses/sources/host_activity*.py`.

## What it is

The first real perceptual input for the organism. On macOS it polls two
permission free signals and tells the Presence State Machine whether
York is at his desk and whether he is engaged.

Before this sensor, the dogfood organism had no senses. The cockpit only
moved when the scheduler fired. This sensor is what makes the dogfood a
real measurement instead of a clock.

## What it reads

- System idle seconds, via Quartz `CGEventSourceSecondsSinceLastEventType`.
  Seconds since the last keyboard or mouse event.
- The frontmost application name, via AppKit `NSWorkspace`.

It does not read window titles or keystroke content. Those would need
macOS Accessibility permission and would capture what York is reading.
Out of scope by design.

## How it maps to the organism

Every poll runs the pure logic in `host_activity_reader.py`:

- Idle under 45 seconds: present and engaged. Publishes
  `PresenceObserved(present=True)` and
  `PostureObserved(at_desk=True, gaze="screen")`. Drives OBSERVING then
  ATTENTIVE.
- Idle 45 to 300 seconds: present, not engaged. `gaze="away"`.
- Idle over 300 seconds: stepped away. `PresenceObserved(present=False)`.
  Drives the organism back toward DORMANT.

## File layout

- `host_activity_reader.py`: pure decision logic. No macOS calls. Tested
  on any platform.
- `host_activity.py`: the macOS I/O layer. Two reader functions plus the
  `HostActivitySource` class. The reader callables are injectable, which
  is how the polling loop is tested without a real Mac.

## Privacy

This sensor watches whether York is active and which app is focused. It
does not read what he types, does not read window contents, stores
nothing, and transmits nothing. It emits two messages onto the same
local bus every other sensor uses.

## What this is not

Not cognition. Not a keylogger. Not a hardware sensor. It is one senses
Source among the eventual several, and it obeys the same Source protocol
as the mock sources.
