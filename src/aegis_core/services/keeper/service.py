"""keeper service — nightly maintenance for the memory store.

Plan C exposes manual triggers:
- consolidate_now() — runs one classification pass over tentative Moments.
- fade_out() — deletes fading Moments older than FADE_LIFETIME_DAYS.

A production deployment wraps these in a scheduled tick (Plan F);
Plan C ships only the manual triggers + the synchronous primitives so the
canonical-cycle test can drive them directly.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import ContinuityCandidate, InterventionClass
from ...storage._conn import connect
from ...storage.moments import MomentStore
from ...storage.schema import run_migrations
from ...storage.themes import ThemeStore
from .._base import AegisService
from .consolidation import FADE_LIFETIME_DAYS, classify_moment
from .theme_tokenizer import tokenize_themes

log = structlog.get_logger()

DEFAULT_DB_PATH = "/tmp/aegis-memory.db"


class KeeperService(AegisService):
    name = "keeper"

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, **kwargs) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path)
        self._conn = None
        self._moments: MomentStore | None = None
        self._themes: ThemeStore | None = None
        self._bus: AegisBus | None = None

    def _open_db(self) -> None:
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._moments = MomentStore(self._conn)
        self._themes = ThemeStore(self._conn)

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        self._open_db()

    async def teardown(self, bus: AegisBus) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

    def consolidate_now(self) -> dict[str, int]:
        """Run one consolidation pass over all tentative Moments.

        Returns count of promotions: {"consolidated": N, "fading": M, "kept": K}.
        Theme keys from consolidated Moments are upserted into ThemeStore.
        """
        if self._moments is None or self._themes is None:
            return {"consolidated": 0, "fading": 0, "kept": 0}
        tentatives = self._moments.query(state="tentative", limit=10_000)
        consolidated = 0
        fading = 0
        kept = 0
        for row in tentatives:
            target = classify_moment(row)
            if target == "consolidated":
                self._moments.promote(row["id"], new_state="consolidated")
                for key in tokenize_themes(row.get("summary")):
                    self._themes.upsert(key)
                consolidated += 1
            elif target == "fading":
                self._moments.promote(row["id"], new_state="fading")
                fading += 1
            else:
                kept += 1
        log.info(
            "keeper.consolidate_now",
            consolidated=consolidated,
            fading=fading,
            kept=kept,
        )
        return {"consolidated": consolidated, "fading": fading, "kept": kept}

    async def consolidate_now_async(self) -> dict[str, int]:
        """Async variant of consolidate_now that also publishes
        memory.continuity_candidate events for newly consolidated Moments.
        """
        if self._moments is None or self._themes is None:
            return {"consolidated": 0, "fading": 0, "kept": 0}
        import json as _json

        tentatives = self._moments.query(state="tentative", limit=10_000)
        consolidated = 0
        fading = 0
        kept = 0
        for row in tentatives:
            target = classify_moment(row)
            if target == "consolidated":
                self._moments.promote(row["id"], new_state="consolidated")
                themes = tokenize_themes(row.get("summary"))
                for key in themes:
                    self._themes.upsert(key)
                consolidated += 1
                if self._bus is not None:
                    sig = _json.loads(row.get("signature_json") or "{}")
                    conf = float(sig.get("focus_score", 0.5))
                    await self._bus.publish(
                        "memory.continuity_candidate",
                        ContinuityCandidate(
                            timestamp=datetime.now(UTC),
                            moment_id=row["id"],
                            moment_summary=row.get("summary") or "",
                            themes=themes,
                            confidence=conf,
                            suggested_class=InterventionClass.MEMORY_MAGIC,
                        ),
                    )
            elif target == "fading":
                self._moments.promote(row["id"], new_state="fading")
                fading += 1
            else:
                kept += 1
        log.info(
            "keeper.consolidate_now_async",
            consolidated=consolidated,
            fading=fading,
            kept=kept,
        )
        return {"consolidated": consolidated, "fading": fading, "kept": kept}

    def fade_out(self) -> int:
        """Delete fading Moments older than FADE_LIFETIME_DAYS. Return count deleted."""
        if self._moments is None or self._conn is None:
            return 0
        cutoff = datetime.now(UTC) - timedelta(days=FADE_LIFETIME_DAYS)
        cur = self._conn.execute(
            """
            DELETE FROM moments
             WHERE state = 'fading'
               AND started_at_utc < ?
            """,
            (cutoff.isoformat(),),
        )
        return int(cur.rowcount or 0)


def make_service(**kwargs) -> KeeperService:
    return KeeperService(**kwargs)
