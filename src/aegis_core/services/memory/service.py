"""memory service — bus → SQLite recorder.

Plan C Task 6: record every senses.* and state.changed event to the DB.
Task 7 adds tentative-Moment management on top.
"""
from __future__ import annotations

from datetime import UTC, datetime  # noqa: F401 — UTC kept for potential use elsewhere
from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import (
    AmbientLightReading,
    PostureObserved,
    PresenceObserved,
    PresenceState,
    StateChanged,
    ThermalReading,
    VoiceActivityDetected,
)
from ...storage._conn import connect
from ...storage.events import EventStore
from ...storage.moments import MomentStore
from ...storage.schema import run_migrations
from .._base import AegisService
from .signature import SignatureAccumulator

log = structlog.get_logger()

DEFAULT_DB_PATH = str(Path.home() / ".aegis-core" / "memory.db")


class MemoryService(AegisService):
    name = "memory"

    # Reflective is part of the canonical organism loop — cognition that
    # happens inside a Reflective window must remain visible to memory.
    _OPEN_STATES = (
        PresenceState.OBSERVING,
        PresenceState.ATTENTIVE,
        PresenceState.REFLECTIVE,
    )

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, **kwargs) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path)
        self._conn = None
        self._events: EventStore | None = None
        self._moments: MomentStore | None = None
        self._open_moment_id: str | None = None
        self._open_signature: SignatureAccumulator | None = None

    def _open_db(self) -> None:
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._events = EventStore(self._conn)
        self._moments = MomentStore(self._conn)

    def _open_moment(self, started_at: datetime, type_: str) -> None:
        if self._moments is None or self._open_moment_id is not None:
            return
        self._open_moment_id = self._moments.open_tentative(
            started_at=started_at, type_=type_
        )
        self._open_signature = SignatureAccumulator()

    def _close_moment(self, ended_at: datetime) -> None:
        if (
            self._moments is None
            or self._open_moment_id is None
            or self._open_signature is None
        ):
            return
        sig = self._open_signature.snapshot()
        summary = self._render_summary(sig)
        self._moments.close(
            self._open_moment_id,
            ended_at=ended_at,
            summary=summary,
            signature=sig,
        )
        self._open_moment_id = None
        self._open_signature = None

    def _render_summary(self, sig: dict) -> str:
        return (
            f"{sig['posture_events']} posture events, "
            f"focus={sig['focus_score']:.2f}, "
            f"voice={sig['voice_events']}"
        )

    def _record(self, subject: str, msg) -> None:
        if self._events is not None:
            self._events.insert(subject, msg)

    async def _on_presence(self, msg: PresenceObserved) -> None:
        self._record("senses.presence", msg)
        if self._open_signature is not None:
            self._open_signature.add_presence(msg)

    async def _on_posture(self, msg: PostureObserved) -> None:
        self._record("senses.posture", msg)
        if self._open_signature is not None:
            self._open_signature.add_posture(msg)

    async def _on_voice(self, msg: VoiceActivityDetected) -> None:
        self._record("senses.voice_activity", msg)
        if self._open_signature is not None:
            self._open_signature.add_voice(msg)

    async def _on_ambient(self, msg: AmbientLightReading) -> None:
        self._record("senses.ambient_light", msg)

    async def _on_thermal(self, msg: ThermalReading) -> None:
        self._record("senses.thermal", msg)

    async def _on_state(self, msg: StateChanged) -> None:
        self._record("state.changed", msg)
        was_open = msg.previous in self._OPEN_STATES
        will_be_open = msg.current in self._OPEN_STATES
        if not was_open and will_be_open:
            if msg.current == PresenceState.ATTENTIVE:
                type_ = "focus_session"
            elif msg.current == PresenceState.REFLECTIVE:
                type_ = "reflective_window"
            else:
                type_ = "observing_window"
            # Moment boundaries derive from EVENT time (msg.timestamp), not
            # wall-clock processing time. This is non-negotiable architecture:
            # the organism timeline must come from the event, not the recipient.
            # Critical for trace replay, accelerated tests, distributed sensors,
            # and any future deterministic replay.
            self._open_moment(started_at=msg.timestamp, type_=type_)
        elif was_open and not will_be_open:
            self._close_moment(ended_at=msg.timestamp)

    async def setup(self, bus: AegisBus) -> None:
        self._open_db()
        self._bus = bus

        await bus.subscribe("senses.presence", PresenceObserved, self._on_presence)
        await bus.subscribe("senses.posture", PostureObserved, self._on_posture)
        await bus.subscribe(
            "senses.voice_activity", VoiceActivityDetected, self._on_voice
        )
        await bus.subscribe(
            "senses.ambient_light", AmbientLightReading, self._on_ambient
        )
        await bus.subscribe("senses.thermal", ThermalReading, self._on_thermal)
        await bus.subscribe("state.changed", StateChanged, self._on_state)

    def query_recent_events(self, limit: int = 100) -> list[dict]:
        if self._events is None:
            return []
        return self._events.recent(limit=limit)

    def query_moments(
        self,
        state: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if self._moments is None:
            return []
        return self._moments.query(state=state, limit=limit)

    def query_themes(self, min_count: int = 1, limit: int = 100) -> list[dict]:
        if self._conn is None:
            return []
        from ...storage.themes import ThemeStore
        return ThemeStore(self._conn).query(min_count=min_count, limit=limit)

    async def teardown(self, bus: AegisBus) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass


def make_service(**kwargs) -> MemoryService:
    return MemoryService(**kwargs)
