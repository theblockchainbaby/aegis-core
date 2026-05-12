"""Mock camera source — replays JPEG+sidecar pairs from a fixtures dir.

Each frame yields exactly one PostureObserved event derived from the
sidecar JSON. The image bytes are read but not analyzed; the mock is
honest about being a fixture replayer.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from ....messages import PostureObserved
from ....messages._base import AegisMessage


class MockCameraSource:
    name = "mock_camera"

    def __init__(self, fixture_dir: Path, real_time: bool = False) -> None:
        self._fixture_dir = Path(fixture_dir)
        self._real_time = real_time

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        frames = sorted(self._fixture_dir.glob("frame_*.json"))
        last_offset = 0
        for json_path in frames:
            data = json.loads(json_path.read_text())
            jpeg_path = json_path.with_suffix(".jpg")
            if jpeg_path.exists():
                _ = jpeg_path.read_bytes()  # touch the bytes; we don't decode

            if self._real_time:
                delta_ms = data.get("offset_ms", 0) - last_offset
                if delta_ms > 0:
                    await asyncio.sleep(delta_ms / 1000.0)
                last_offset = data.get("offset_ms", 0)

            msg = PostureObserved(
                timestamp=datetime.now(UTC),
                at_desk=data["at_desk"],
                gaze=data["gaze"],
                movement_score=data["movement_score"],
            )
            yield "senses.posture", msg

    async def aclose(self) -> None:
        pass
