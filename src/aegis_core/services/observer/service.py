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
    PresenceState,
    StateChanged,
    UtteranceProposal,
    VoiceSpeak,
)
from .._base import AegisService
from .app import build_app
from .ring_buffer import BufferedEvent, EventRingBuffer
from .scheduler import Scheduler, load_schedule

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
        schedule_path: str | Path | None = None,
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
        self._scheduler: Scheduler | None = None
        self._schedule_path = (
            Path(schedule_path)
            if schedule_path is not None
            else Path(__file__).resolve().parents[4] / "rules" / "schedule.yaml"
        )
        self._scheduler_task: asyncio.Task | None = None
        self._bus_ref: AegisBus | None = None

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
        self._bus_ref = bus
        self._app.state.bus = bus
        try:
            self._scheduler = Scheduler(load_schedule(self._schedule_path))
        except FileNotFoundError:
            log.warning("scheduler.config_missing", path=str(self._schedule_path))

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
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        # Wait until shutdown is requested, then stop uvicorn.
        await self._shutdown.wait()
        self._uvicorn_server.should_exit = True
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except (asyncio.CancelledError, BaseException):
                pass
        if self._uvicorn_task is not None:
            try:
                await asyncio.wait_for(self._uvicorn_task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError):
                pass

    async def _append(self, subject: str, msg) -> None:
        event = BufferedEvent(
            subject=subject,
            timestamp=datetime.now(UTC),
            payload=msg.model_dump(mode="json"),
        )
        self._buffer.append(event)
        # Push to SSE clients.
        from .app import broadcast_event
        await broadcast_event(self._app, event)

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

    async def _scheduler_loop(self) -> None:
        log.info(
            "observer.scheduler_loop_started",
            schedule_path=str(self._schedule_path),
            scheduler_present=self._scheduler is not None,
        )
        while not self._shutdown.is_set():
            await asyncio.sleep(30)
            if self._scheduler is None or self._bus_ref is None:
                log.warning(
                    "observer.scheduler_tick_skipped",
                    scheduler_present=self._scheduler is not None,
                    bus_ref_present=self._bus_ref is not None,
                )
                continue
            now = datetime.now(UTC)
            triggers = self._scheduler.tick(now=now)
            log.info(
                "observer.scheduler_tick",
                now=now.isoformat(),
                n_triggers=len(triggers),
            )
            for t in triggers:
                try:
                    target = PresenceState(t.target_state)
                except ValueError:
                    log.warning(
                        "observer.scheduler_unknown_state",
                        target_state=t.target_state,
                    )
                    continue
                log.info(
                    "observer.scheduler_trigger_fired",
                    name=t.name,
                    target_state=t.target_state,
                    reason=t.reason,
                )
                await self._bus_ref.publish(
                    "state.changed",
                    StateChanged(
                        timestamp=datetime.now(UTC),
                        # TEMPORARY (Plan F'): the scheduler doesn't yet know the
                        # current presence state. previous=DORMANT is a placeholder
                        # that the real Presence State Machine reconciles. Do NOT
                        # let this harden into protocol — Plan F' must read the
                        # buffer's most recent state.changed and use its current
                        # as the `previous` value here.
                        previous=PresenceState.DORMANT,
                        current=target,
                        reason=t.reason,
                    ),
                )


def make_service(**kwargs) -> ObserverService:
    return ObserverService(**kwargs)
