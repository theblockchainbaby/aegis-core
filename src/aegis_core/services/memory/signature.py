"""SignatureAccumulator — per-Moment summary statistic block.

Pure logic. Events go in via add_*() methods; snapshot() returns a dict
suitable for serialization into the moments.signature_json column.
"""
from __future__ import annotations

from typing import Any

from ...messages import (
    PostureObserved,
    PresenceObserved,
    VoiceActivityDetected,
)


class SignatureAccumulator:
    def __init__(self) -> None:
        self._posture_events = 0
        self._on_screen = 0
        self._movement_total = 0.0
        self._voice_events_active = 0
        self._voice_events_total = 0
        self._presence_events = 0
        self._presence_lost = 0

    def add_posture(self, msg: PostureObserved) -> None:
        self._posture_events += 1
        if msg.at_desk and msg.gaze == "screen":
            self._on_screen += 1
        self._movement_total += msg.movement_score

    def add_voice(self, msg: VoiceActivityDetected) -> None:
        self._voice_events_total += 1
        if msg.active:
            self._voice_events_active += 1

    def add_presence(self, msg: PresenceObserved) -> None:
        self._presence_events += 1
        if not msg.present:
            self._presence_lost += 1

    def snapshot(self) -> dict[str, Any]:
        focus_score = (
            self._on_screen / self._posture_events if self._posture_events else 0.0
        )
        movement_score = (
            self._movement_total / self._posture_events if self._posture_events else 0.0
        )
        return {
            "posture_events": self._posture_events,
            "voice_events": self._voice_events_active,
            "voice_events_total": self._voice_events_total,
            "presence_events": self._presence_events,
            "presence_lost": self._presence_lost,
            "focus_score": focus_score,
            "movement_score": movement_score,
        }
