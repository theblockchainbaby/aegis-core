"""Mock ambient-light + thermal source — emits parametric constant readings.

Useful for the canonical-cycle integration test where the exact lux/celsius
don't matter — only that the events flow.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from ....messages import AmbientLightReading, ThermalReading
from ....messages._base import AegisMessage


class MockEnvironmentSource:
    name = "mock_environment"

    def __init__(
        self,
        lux: float = 250.0,
        celsius: float = 42.0,
        ticks: int = 10,
        real_time: bool = False,
    ) -> None:
        self._lux = lux
        self._celsius = celsius
        self._ticks = ticks
        self._real_time = real_time

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        for _ in range(self._ticks):
            now = datetime.now(UTC)
            yield "senses.ambient_light", AmbientLightReading(timestamp=now, lux=self._lux)
            yield "senses.thermal", ThermalReading(timestamp=now, celsius=self._celsius)
            if self._real_time:
                await asyncio.sleep(1.0)

    async def aclose(self) -> None:
        pass
