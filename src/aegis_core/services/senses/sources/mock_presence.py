"""Mock presence source — replays mmWave-equivalent events from a JSON trace.

Trace format:
  [{"offset_ms": int, "present": bool, "confidence": float}, ...]

Events are yielded in order. If `real_time=True`, the source sleeps between
events to match the recorded cadence.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from ....messages import PresenceObserved
from ....messages._base import AegisMessage


class MockPresenceSource:
    name = "mock_presence"

    def __init__(self, trace_path: str | Path, real_time: bool = False) -> None:
        self._path = Path(trace_path)
        self._real_time = real_time

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        trace = json.loads(self._path.read_text())
        last_offset = 0
        for entry in trace:
            if self._real_time:
                delta_ms = entry["offset_ms"] - last_offset
                if delta_ms > 0:
                    await asyncio.sleep(delta_ms / 1000.0)
                last_offset = entry["offset_ms"]
            msg = PresenceObserved(
                timestamp=datetime.now(UTC),
                present=entry["present"],
                source="mmwave",
                confidence=entry["confidence"],
            )
            yield "senses.presence", msg

    async def aclose(self) -> None:
        pass
