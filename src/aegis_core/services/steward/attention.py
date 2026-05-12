"""AttentionSignals — source of 'is the user currently busy?' bits.

Plan D ships only the Stub and a Programmable variant for tests. Plan E
wires real signals (keystroke detector, audio profile, OS active-window
tracking) behind the same Protocol.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AttentionSignals(Protocol):
    def is_typing(self) -> bool: ...
    def is_in_call(self) -> bool: ...
    def is_video_playing(self) -> bool: ...
    def seconds_since_last_pause(self) -> float: ...


class StubAttentionSignals:
    """No competing activity ever. Default for Plan D."""

    def is_typing(self) -> bool:
        return False

    def is_in_call(self) -> bool:
        return False

    def is_video_playing(self) -> bool:
        return False

    def seconds_since_last_pause(self) -> float:
        return 30.0  # ample pause


class ProgrammableAttentionSignals:
    """Test-only signal source with explicit setters."""

    def __init__(self) -> None:
        self._typing = False
        self._in_call = False
        self._video_playing = False
        self._seconds_pause = 30.0

    def set_typing(self, value: bool) -> None:
        self._typing = value

    def set_in_call(self, value: bool) -> None:
        self._in_call = value

    def set_video_playing(self, value: bool) -> None:
        self._video_playing = value

    def set_seconds_since_last_pause(self, value: float) -> None:
        self._seconds_pause = value

    def is_typing(self) -> bool:
        return self._typing

    def is_in_call(self) -> bool:
        return self._in_call

    def is_video_playing(self) -> bool:
        return self._video_playing

    def seconds_since_last_pause(self) -> float:
        return self._seconds_pause
