"""Mock audio source — reads a WAV file and emits VAD events at 10 Hz.

The "VAD" is a trivial RMS threshold suitable for fixtures, not production.
Plan B' replaces this with a real silero-vad-driven source.
"""
from __future__ import annotations

import asyncio
import math
import wave
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from ....messages import VoiceActivityDetected
from ....messages._base import AegisMessage


WINDOW_MS = 100
ACTIVITY_RMS_DB_THRESHOLD = -36.0  # below this we call it inactive


def _rms_db(samples: list[int]) -> float:
    if not samples:
        return -120.0
    sq = sum(s * s for s in samples) / len(samples)
    if sq <= 0:
        return -120.0
    rms = math.sqrt(sq)
    return 20.0 * math.log10(rms / 32768.0)


class MockAudioSource:
    name = "mock_audio"

    def __init__(self, wav_path: Path, real_time: bool = False) -> None:
        self._path = Path(wav_path)
        self._real_time = real_time

    async def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        with wave.open(str(self._path), "rb") as wf:
            assert wf.getnchannels() == 1
            rate = wf.getframerate()
            samples_per_window = rate * WINDOW_MS // 1000
            raw_bytes_per_window = samples_per_window * wf.getsampwidth()

            import struct

            while True:
                chunk = wf.readframes(samples_per_window)
                if len(chunk) < raw_bytes_per_window:
                    break
                samples = list(
                    struct.unpack(f"<{samples_per_window}h", chunk)
                )
                rms_db = _rms_db(samples)
                msg = VoiceActivityDetected(
                    timestamp=datetime.now(UTC),
                    active=rms_db > ACTIVITY_RMS_DB_THRESHOLD,
                    rms_db=rms_db,
                    confidence=0.7,
                )
                yield "senses.voice_activity", msg
                if self._real_time:
                    await asyncio.sleep(WINDOW_MS / 1000.0)

    async def aclose(self) -> None:
        pass
