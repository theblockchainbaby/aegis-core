"""Brain Reverie — graceful behavioral expression of a Jetson stall.

If the heartbeat link goes silent for > REVERIE_TIMEOUT_MS, the MCU:
- emits REVERIE_ENTER
- slows breath cadence by +1.5 s
- dims palette by 30 %

On the next valid frame, restores prior cadence + brightness and emits
REVERIE_EXIT. The user sees a slightly slower drift, never an error state.
"""
try:
    import time
    _ = time.ticks_ms  # MicroPython
except AttributeError:
    # CPython fallback so the module is testable on the host.
    import time as _t

    class _CompatTime:
        @staticmethod
        def ticks_ms() -> int:
            return int(_t.monotonic() * 1000)

        @staticmethod
        def ticks_diff(a: int, b: int) -> int:
            return a - b

    time = _CompatTime

REVERIE_TIMEOUT_MS = 5000


class ReverieMonitor:
    def __init__(self) -> None:
        self._last_frame_ms = time.ticks_ms()
        self._in_reverie = False

    def note_frame(self) -> None:
        self._last_frame_ms = time.ticks_ms()

    @property
    def in_reverie(self) -> bool:
        return self._in_reverie

    def check(self) -> str | None:
        """Return 'enter' or 'exit' on a transition; None otherwise."""
        elapsed = time.ticks_diff(time.ticks_ms(), self._last_frame_ms)
        if not self._in_reverie and elapsed > REVERIE_TIMEOUT_MS:
            self._in_reverie = True
            return "enter"
        if self._in_reverie and elapsed <= REVERIE_TIMEOUT_MS:
            self._in_reverie = False
            return "exit"
        return None
