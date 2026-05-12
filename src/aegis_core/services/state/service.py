"""state service — Presence State Machine on the bus.

Subscribes to senses.* events, ticks the machine on a regular cadence, and
publishes state.changed for every transition.

The `accelerate_for_test` parameter speeds up the internal clock for tests;
production uses 1.0 (real-time).
"""
from __future__ import annotations

import asyncio
import time

import structlog

from ...bus import AegisBus
from ...messages import (
    PostureObserved,
    PresenceObserved,
    StateChanged,
    VoiceActivityDetected,
)
from .._base import AegisService
from .machine import PresenceStateMachine

log = structlog.get_logger()


class StateService(AegisService):
    name = "state"

    def __init__(
        self,
        tick_ms: int = 250,
        accelerate_for_test: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._tick_ms = tick_ms
        self._accelerate = accelerate_for_test
        self._machine = PresenceStateMachine()
        self._bus: AegisBus | None = None

    async def _emit(self, transition: StateChanged | None) -> None:
        if transition and self._bus is not None:
            await self._bus.publish("state.changed", transition)

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus

        async def on_presence(msg: PresenceObserved) -> None:
            await self._emit(self._machine.observe_presence(msg))

        async def on_posture(msg: PostureObserved) -> None:
            await self._emit(self._machine.observe_posture(msg))

        async def on_voice(msg: VoiceActivityDetected) -> None:
            await self._emit(self._machine.observe_voice(msg))

        await bus.subscribe("senses.presence", PresenceObserved, on_presence)
        await bus.subscribe("senses.posture", PostureObserved, on_posture)
        await bus.subscribe("senses.voice_activity", VoiceActivityDetected, on_voice)

    async def main(self, bus: AegisBus) -> None:
        async def tick_loop() -> None:
            wall_interval = (self._tick_ms / 1000.0) / self._accelerate
            virtual_ms = int(self._tick_ms)
            while not self._shutdown.is_set():
                await asyncio.sleep(wall_interval)
                self._machine.tick_ms(virtual_ms)
                await self._emit(self._machine.elapse())

        task = asyncio.create_task(tick_loop())
        try:
            await self._shutdown.wait()
        finally:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


def make_service(**kwargs) -> StateService:
    return StateService(**kwargs)
