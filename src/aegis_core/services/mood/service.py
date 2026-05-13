"""mood service — state-driven mood event publisher.

Plan E publishes a MoodChanged event on every state.changed received.
Downstream consumers (MCU LED heartbeat in Plan A Task 19+, Plan F's
observer cockpit) render these.
"""
from __future__ import annotations

import structlog

from ...bus import AegisBus
from ...messages import StateChanged
from .._base import AegisService
from .inference import MoodSignals, infer_mood

log = structlog.get_logger()


class MoodService(AegisService):
    name = "mood"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bus: AegisBus | None = None

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        await bus.subscribe("state.changed", StateChanged, self._on_state)

    async def _on_state(self, msg: StateChanged) -> None:
        if self._bus is None:
            return
        mood = infer_mood(state=msg.current, signals=MoodSignals())
        await self._bus.publish("mood.changed", mood)


def make_service(**kwargs) -> MoodService:
    return MoodService(**kwargs)
