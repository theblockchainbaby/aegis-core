"""observer service — bus subscriber + uvicorn lifecycle.

Subscribes to all major bus subjects, fills a shared EventRingBuffer, and
serves the FastAPI app on 127.0.0.1:8080 (localhost-only).
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import structlog
import uvicorn

from ...bus import AegisBus
from ...messages import (
    ContinuityCandidate,
    MoodChanged,
    StateChanged,
    UtteranceProposal,
    VoiceSpeak,
)
from .._base import AegisService
from .app import build_app
from .ring_buffer import BufferedEvent, EventRingBuffer

log = structlog.get_logger()

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_DB_PATH = "/tmp/aegis-memory.db"
DEFAULT_BUFFER_CAPACITY = 500


class ObserverService(AegisService):
    name = "observer"

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        db_path: str | Path = DEFAULT_DB_PATH,
        buffer_capacity: int = DEFAULT_BUFFER_CAPACITY,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._host = host
        self._port = port
        self._db_path = Path(db_path)
        self._buffer = EventRingBuffer(capacity=buffer_capacity)
        self._app = build_app(buffer=self._buffer, db_path=self._db_path)
        self._uvicorn_task: asyncio.Task | None = None
        self._uvicorn_server: uvicorn.Server | None = None

    async def setup(self, bus: AegisBus) -> None:
        await bus.subscribe("state.changed", StateChanged, self._on_state)
        await bus.subscribe("mood.changed", MoodChanged, self._on_mood)
        await bus.subscribe("voice.speak", VoiceSpeak, self._on_voice)
        await bus.subscribe(
            "mind.utterance_proposal", UtteranceProposal, self._on_proposal
        )
        await bus.subscribe(
            "memory.continuity_candidate", ContinuityCandidate, self._on_candidate
        )

    async def main(self, bus: AegisBus) -> None:
        config = uvicorn.Config(
            app=self._app,
            host=self._host,
            port=self._port,
            log_level="warning",
            access_log=False,
        )
        self._uvicorn_server = uvicorn.Server(config)
        self._uvicorn_task = asyncio.create_task(
            self._uvicorn_server.serve()
        )
        # Wait until shutdown is requested, then stop uvicorn.
        await self._shutdown.wait()
        self._uvicorn_server.should_exit = True
        if self._uvicorn_task is not None:
            try:
                await asyncio.wait_for(self._uvicorn_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

    async def _append(self, subject: str, msg) -> None:
        self._buffer.append(
            BufferedEvent(
                subject=subject,
                timestamp=datetime.now(UTC),
                payload=msg.model_dump(mode="json"),
            )
        )

    async def _on_state(self, msg: StateChanged) -> None:
        await self._append("state.changed", msg)

    async def _on_mood(self, msg: MoodChanged) -> None:
        await self._append("mood.changed", msg)

    async def _on_voice(self, msg: VoiceSpeak) -> None:
        await self._append("voice.speak", msg)

    async def _on_proposal(self, msg: UtteranceProposal) -> None:
        await self._append("mind.utterance_proposal", msg)

    async def _on_candidate(self, msg: ContinuityCandidate) -> None:
        await self._append("memory.continuity_candidate", msg)


def make_service(**kwargs) -> ObserverService:
    return ObserverService(**kwargs)
