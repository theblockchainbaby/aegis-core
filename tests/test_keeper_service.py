import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aegis_core.services.keeper.service import KeeperService
from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations
from aegis_core.storage.themes import ThemeStore


def _seed_moment(
    conn,
    started: datetime,
    ended: datetime | None,
    summary: str,
    signature: dict,
) -> str:
    store = MomentStore(conn)
    mid = store.open_tentative(started_at=started, type_="focus_session")
    if ended is not None:
        store.close(mid, ended_at=ended, summary=summary, signature=signature)
    return mid


def test_consolidate_now_promotes_real_focus(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    start = datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC)
    mid = _seed_moment(
        conn,
        started=start,
        ended=start + timedelta(minutes=20),
        summary="Long focused session at desk on the landing page redesign.",
        signature={"posture_events": 14, "voice_events": 0, "focus_score": 0.92},
    )
    conn.close()

    keeper = KeeperService(db_path=db)
    keeper._open_db()
    counts = keeper.consolidate_now()
    assert counts["consolidated"] == 1
    assert counts["fading"] == 0

    conn = connect(db)
    state = MomentStore(conn).get(mid)["state"]
    assert state == "consolidated"
    # Themes extracted from the summary.
    themes = {t["key"] for t in ThemeStore(conn).query()}
    assert "landing" in themes
    assert "redesign" in themes
    conn.close()


def test_consolidate_now_fades_thin_session(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    start = datetime(2026, 5, 11, 10, 0, 0, tzinfo=UTC)
    mid = _seed_moment(
        conn,
        started=start,
        ended=start + timedelta(seconds=10),
        summary="brief glance",
        signature={"posture_events": 1, "voice_events": 0, "focus_score": 0.1},
    )
    conn.close()

    keeper = KeeperService(db_path=db)
    keeper._open_db()
    counts = keeper.consolidate_now()
    assert counts["fading"] == 1

    conn = connect(db)
    assert MomentStore(conn).get(mid)["state"] == "fading"
    conn.close()


def test_fade_out_deletes_old_fading(tmp_path: Path):
    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    long_ago = datetime.now(UTC) - timedelta(days=10)
    mid = _seed_moment(
        conn,
        started=long_ago,
        ended=long_ago + timedelta(seconds=60),
        summary="old",
        signature={"posture_events": 1},
    )
    MomentStore(conn).promote(mid, new_state="fading")
    conn.close()

    keeper = KeeperService(db_path=db)
    keeper._open_db()
    deleted = keeper.fade_out()
    assert deleted == 1

    conn = connect(db)
    assert MomentStore(conn).get(mid) is None
    conn.close()
