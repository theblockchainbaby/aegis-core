"""TraceRunner — replays a canonical-cycle JSON fixture as a single Source.

The fixture format:
{
  "duration_s": int,
  "presence_events": [{"offset_ms": int, "present": bool, "confidence": float}],
  "posture_events":  [{"offset_ms": int, "at_desk": bool, "gaze": str, "movement_score": float}],
  "voice_events":    [{"offset_ms": int, "active": bool, "rms_db": float, "confidence": float}]
}

Events from all three sections are merged and yielded in offset order. If
real_time=True, the runner sleeps between events to match the recorded cadence.
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

    def __init__(self, fixture_path: str | Path, real_time: bool = False) -> None:
        self._fixture = json.loads(Path(fixture_path).read_text())
        self._real_time = real_time

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        entries = _normalize(self._fixture)
        last_offset = 0
        for offset_ms, subject, data, model in entries:
            if self._real_time:
                delta_ms = offset_ms - last_offset
                if delta_ms > 0:
                    await asyncio.sleep(delta_ms / 1000.0)
                last_offset = offset_ms
            yield subject, _construct(model, data)

    async def aclose(self) -> None:
        pass
