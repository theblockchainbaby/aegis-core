"""VoiceBackend — pluggable interface for utterance rendering.

Plan E ships StdoutBackend (prints + log file). Plan E' adds PiperBackend
for real TTS.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Protocol, runtime_checkable


@runtime_checkable
class VoiceBackend(Protocol):
    async def speak(self, text: str) -> None: ...


class StdoutBackend:
    """Prints utterances to a stream (default: stdout) and optionally to a log file.

    The log file is append-only and gets a [HH:MM:SS] timestamp prefix per line.
    """

    def __init__(
        self,
        stream: IO[str] | None = None,
        log_path: str | Path | None = "/tmp/aegis-voice.log",
    ) -> None:
        self._stream = stream if stream is not None else sys.stdout
        self._log_path = Path(log_path) if log_path is not None else None

    async def speak(self, text: str) -> None:
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self._stream.write(line)
        try:
            self._stream.flush()
        except Exception:
            pass
        if self._log_path is not None:
            try:
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError:
                pass
