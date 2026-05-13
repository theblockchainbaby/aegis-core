"""mind service — cognition router on the bus.

Plan E replaces the Plan D mock with a real implementation that:
  - subscribes to state.changed and memory.continuity_candidate
  - on REFLECTIVE entry:
      1. uses a fresh cached ContinuityCandidate event if one exists, OR
      2. queries the memory store for a recent consolidated Moment and
         constructs a ContinuityCandidate on the fly
  - runs the cognition router with whichever candidate (if any)
  - publishes mind.utterance_proposal events for the Steward

The two candidate paths (event-driven + pull-driven) are non-negotiable.
Keeper runs nightly/maintenance; reflective cognition is runtime. Memory
Magic Moments consolidated days ago should still surface today.

Plan E uses StubClaudeClient (no real API calls). Plan E' swaps to
AnthropicClient without changing this service.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import (
    ContinuityCandidate,
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from ...storage._conn import connect
from ...storage.moments import MomentStore
from ...storage.schema import run_migrations
from ...storage.themes import ThemeStore
from .._base import AegisService
from .claude_client import ClaudeClient, StubClaudeClient
from .local_generator import GeneratorContext
from .router import route

log = structlog.get_logger()

DEFAULT_DB_PATH = "/tmp/aegis-memory.db"
# Discard cached ContinuityCandidate events older than this.
CANDIDATE_TTL_SECONDS = 60.0
# Retrieval path: how far back to look for consolidated Moments.
RETRIEVAL_WINDOW_DAYS = 7


class MindService(AegisService):
    name = "mind"

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        claude: ClaudeClient | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path)
        self._claude: ClaudeClient = claude or StubClaudeClient()
        self._bus: AegisBus | None = None
        self._pending_candidate: ContinuityCandidate | None = None
        self._pending_at: datetime | None = None
        self._presence_state: PresenceState = PresenceState.DORMANT

        # Memory access (read-mostly, but the connect() helper opens RW).
        self._conn = None
        self._moments: MomentStore | None = None
        self._themes: ThemeStore | None = None

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        # Open memory DB for runtime retrieval queries.
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._moments = MomentStore(self._conn)
        self._themes = ThemeStore(self._conn)

        await bus.subscribe("state.changed", StateChanged, self._on_state)
        await bus.subscribe(
            "memory.continuity_candidate",
            ContinuityCandidate,
            self._on_candidate,
        )

    async def teardown(self, bus: AegisBus) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

    async def _on_candidate(self, msg: ContinuityCandidate) -> None:
        self._pending_candidate = msg
        self._pending_at = datetime.now(UTC)

    async def _on_state(self, msg: StateChanged) -> None:
        self._presence_state = msg.current

        if msg.current != PresenceState.REFLECTIVE:
            return
        if self._bus is None:
            return

        # Path 1: fresh ContinuityCandidate event (keeper-published, runtime).
        candidate = self._fresh_candidate()
        if candidate is not None:
            self._pending_candidate = None
            self._pending_at = None
        else:
            # Path 2: runtime retrieval from already-consolidated Moments.
            candidate = self._query_recent_consolidated_moment()

        gen_ctx = GeneratorContext(
            presence_state=msg.current,
            now=datetime.now(UTC),
            moment_open_for_seconds=None,  # Plan E: not wired yet
            themes=[],
        )
        proposal = await route(
            gen_ctx=gen_ctx,
            candidate=candidate,
            claude=self._claude,
        )
        if proposal is None:
            return
        await self._bus.publish("mind.utterance_proposal", proposal)

    def _fresh_candidate(self) -> ContinuityCandidate | None:
        if self._pending_candidate is None or self._pending_at is None:
            return None
        age = (datetime.now(UTC) - self._pending_at).total_seconds()
        if age > CANDIDATE_TTL_SECONDS:
            self._pending_candidate = None
            self._pending_at = None
            return None
        return self._pending_candidate

    def _query_recent_consolidated_moment(self) -> ContinuityCandidate | None:
        """Pull a recent consolidated Moment for runtime Memory-Magic surfacing.

        Returns the most recent consolidated Moment within RETRIEVAL_WINDOW_DAYS,
        or None. This is the path that lets Memory Magic Moments fire on any
        future REFLECTIVE, not only on the night they consolidated.
        """
        if self._moments is None or self._themes is None:
            return None
        candidates = self._moments.query(state="consolidated", limit=20)
        if not candidates:
            return None
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=RETRIEVAL_WINDOW_DAYS)
        fresh = [
            m for m in candidates
            if datetime.fromisoformat(m["started_at_utc"]) >= cutoff
        ]
        if not fresh:
            return None
        row = fresh[0]  # most recent first (MomentStore.query orders DESC)
        summary = row.get("summary") or ""
        sig = json.loads(row.get("signature_json") or "{}")
        conf = float(sig.get("focus_score", 0.5))
        theme_rows = self._themes.query(limit=5)
        themes = [t["key"] for t in theme_rows]
        return ContinuityCandidate(
            timestamp=now,
            moment_id=row["id"],
            moment_summary=summary,
            themes=themes,
            confidence=conf,
            suggested_class=InterventionClass.MEMORY_MAGIC,
        )


def make_service(**kwargs) -> MindService:
    return MindService(**kwargs)
