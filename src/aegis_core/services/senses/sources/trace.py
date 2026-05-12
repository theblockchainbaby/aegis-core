"""TraceRunner — replays a canonical-cycle JSON fixture as a single Source.

The fixture format:
{
  "duration_s": int,
  "presence_events": [{"offset_ms": int, "present": bool, "confidence": float}],
  "posture_events":  [{"offset_ms": int, "at_desk": bool, "gaze": str, "movement_score": float}],
  "voice_events":    [{"offset_ms": int, "active": bool, "rms_db": float, "confidence": float}]
}

Events from all three sections are merged and yielded in offset order.

Pacing modes:
- real_time=False, min_pacing_ms=0    → burst (no sleep between events)
- real_time=False, min_pacing_ms=N    → uniform N ms wall-clock between events
- real_time=True,  min_pacing_ms=0    → honor recorded offset_ms cadence exactly
- real_time=True,  min_pacing_ms=N    → recorded cadence with N ms floor
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from ....messages import (
    AegisMessage,
    PostureObserved,
    PresenceObserved,
    VoiceActivityDetected,
)


def _normalize(trace: dict) -> list[tuple[int, str, dict, type[AegisMessage]]]:
    out: list[tuple[int, str, dict, type[AegisMessage]]] = []
    for e in trace.get("presence_events", []):
        out.append((e["offset_ms"], "senses.presence", e, PresenceObserved))
    for e in trace.get("posture_events", []):
        out.append((e["offset_ms"], "senses.posture", e, PostureObserved))
    for e in trace.get("voice_events", []):
        out.append((e["offset_ms"], "senses.voice_activity", e, VoiceActivityDetected))
    out.sort(key=lambda t: t[0])
    return out


def _construct(model: type[AegisMessage], data: dict) -> AegisMessage:
    payload = {k: v for k, v in data.items() if k != "offset_ms"}
    payload.setdefault("timestamp", datetime.now(UTC).isoformat())
    if model is PresenceObserved:
        payload.setdefault("source", "mmwave")
    return model.model_validate(payload)


class TraceRunner:
    name = "trace_runner"

    def __init__(
        self,
        fixture_path: str | Path,
        real_time: bool = False,
        min_pacing_ms: int = 0,
    ) -> None:
        self._fixture = json.loads(Path(fixture_path).read_text())
        self._real_time = real_time
        self._min_pacing_ms = max(0, int(min_pacing_ms))

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        entries = _normalize(self._fixture)
        last_offset = 0
        for i, (offset_ms, subject, data, model) in enumerate(entries):
            if self._real_time:
                delta_ms = offset_ms - last_offset
                sleep_ms = max(delta_ms, self._min_pacing_ms)
            else:
                sleep_ms = self._min_pacing_ms if i > 0 else 0
            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000.0)
            last_offset = offset_ms
            yield subject, _construct(model, data)

    async def aclose(self) -> None:
        pass
