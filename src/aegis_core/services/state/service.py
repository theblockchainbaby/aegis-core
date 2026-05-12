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
    AmbientLightReading,
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
    VoiceActivityDetected,
)
from .._base import AegisService
from .machine import PresenceStateMachine
from .rules import MIN_DWELL_MS

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
        self._settling_target: PresenceState | None = None

    async def _emit(self, transition: StateChanged | None) -> None:
        if transition and self._bus is not None:
            await self._bus.publish("state.changed", transition)
            # If we routed via Settling, remember the intended target so we
            # can resume after dwell.
            if transition.current == PresenceState.SETTLING and transition.reason.startswith(
                "settling_for:"
            ):
                self._settling_target = None  # Plan B: don't auto-resume targets we don't know

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

        async def on_ambient(msg: AmbientLightReading) -> None:
            await self._emit(self._machine.observe_ambient_light(msg))

        await bus.subscribe("senses.ambient_light", AmbientLightReading, on_ambient)

    async def main(self, bus: AegisBus) -> None:
        async def tick_loop() -> None:
            wall_interval = (self._tick_ms / 1000.0) / self._accelerate
            virtual_ms = int(self._tick_ms)
            while not self._shutdown.is_set():
                await asyncio.sleep(wall_interval)
                self._machine.tick_ms(virtual_ms)
                await self._emit(self._machine.elapse())
                # Auto-leave Settling once dwell expires, back to the previous workable state.
                if (
                    self._machine.current == PresenceState.SETTLING
                    and self._machine.dwell_ms >= MIN_DWELL_MS[PresenceState.SETTLING]
                ):
                    follow_up = self._machine.request_transition(
                        PresenceState.ATTENTIVE,
                        "settling_complete",
                    )
                    await self._emit(follow_up)

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
