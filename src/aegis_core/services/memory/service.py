"""memory service — bus → SQLite recorder.

Plan C Task 6: record every senses.* and state.changed event to the DB.
Task 7 adds tentative-Moment management on top.
"""
from __future__ import annotations

from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import (
    AmbientLightReading,
    PostureObserved,
    PresenceObserved,
    StateChanged,
    ThermalReading,
    VoiceActivityDetected,
)
from ...storage._conn import connect
from ...storage.events import EventStore
from ...storage.schema import run_migrations
from .._base import AegisService

log = structlog.get_logger()

DEFAULT_DB_PATH = "/tmp/aegis-memory.db"


class MemoryService(AegisService):
    name = "memory"

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, **kwargs) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path)
        self._conn = None
        self._events: EventStore | None = None

    def _open_db(self) -> None:
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._events = EventStore(self._conn)

    async def setup(self, bus: AegisBus) -> None:
        self._open_db()

        async def record(subject: str, msg) -> None:
            if self._events is not None:
                self._events.insert(subject, msg)

        async def on_presence(msg: PresenceObserved) -> None:
            await record("senses.presence", msg)

        async def on_posture(msg: PostureObserved) -> None:
            await record("senses.posture", msg)

        async def on_voice(msg: VoiceActivityDetected) -> None:
            await record("senses.voice_activity", msg)

        async def on_ambient(msg: AmbientLightReading) -> None:
            await record("senses.ambient_light", msg)

        async def on_thermal(msg: ThermalReading) -> None:
            await record("senses.thermal", msg)

        async def on_state(msg: StateChanged) -> None:
            await record("state.changed", msg)

        await bus.subscribe("senses.presence", PresenceObserved, on_presence)
        await bus.subscribe("senses.posture", PostureObserved, on_posture)
        await bus.subscribe(
            "senses.voice_activity", VoiceActivityDetected, on_voice
        )
        await bus.subscribe(
            "senses.ambient_light", AmbientLightReading, on_ambient
        )
        await bus.subscribe("senses.thermal", ThermalReading, on_thermal)
        await bus.subscribe("state.changed", StateChanged, on_state)

    async def teardown(self, bus: AegisBus) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass


def make_service(**kwargs) -> MemoryService:
    return MemoryService(**kwargs)
