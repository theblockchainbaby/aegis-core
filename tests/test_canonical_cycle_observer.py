"""Plan F capstone — cockpit reads the live canonical cycle."""
import asyncio
import io
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    PresenceState,
    StateChanged,
)
from aegis_core.services.keeper.service import KeeperService
from aegis_core.services.mind.service import MindService
from aegis_core.services.mood.service import MoodService
from aegis_core.services.observer.service import ObserverService
from aegis_core.services.steward.service import StewardService
from aegis_core.services.voice.backend import StdoutBackend
from aegis_core.services.voice.service import VoiceService
from aegis_core.storage._conn import connect
from aegis_core.storage.moments import MomentStore
from aegis_core.storage.schema import run_migrations

REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


def _seed_consolidatable_moment(db_path: Path) -> str:
    conn = connect(db_path)
    run_migrations(conn)
    start = datetime(2026, 5, 11, 9, 0, 0, tzinfo=UTC)
    store = MomentStore(conn)
    mid = store.open_tentative(started_at=start, type_="focus_session")
    store.close(
        mid,
        ended_at=start + timedelta(minutes=22),
        summary="Long focused session on the landing page redesign.",
        signature={
            "posture_events": 14,
            "voice_events": 0,
            "focus_score": 0.92,
        },
    )
    conn.close()
    return mid


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_capstone_cockpit_reflects_full_cycle(
    nats_server, tmp_path: Path
):
    db_path = tmp_path / "m.db"
    _seed_consolidatable_moment(db_path)
    port = _free_port()

    voice_buf = io.StringIO()
    services = [
        VoiceService(
            nats_url=nats_server,
            backend=StdoutBackend(stream=voice_buf, log_path=tmp_path / "v.log"),
        ),
        MindService(nats_url=nats_server, db_path=db_path),
        StewardService(
            nats_url=nats_server, db_path=db_path, rules_path=REPO_RULES
        ),
        MoodService(nats_url=nats_server),
        ObserverService(
            nats_url=nats_server,
            host="127.0.0.1",
            port=port,
            db_path=db_path,
            schedule_path=str(REPO_RULES.parent / "schedule.yaml"),
        ),
    ]
    tasks = [asyncio.create_task(s.run()) for s in services]
    await asyncio.sleep(0.8)

    # Use keeper to publish ContinuityCandidate.
    keeper = KeeperService(db_path=db_path)
    async with AegisBus.connect(nats_server) as keeper_bus:
        keeper._open_db()
        keeper._bus = keeper_bus
        await keeper.consolidate_now_async()
        await keeper_bus.flush()
        await asyncio.sleep(0.3)

    # Drive REFLECTIVE.
    async with AegisBus.connect(nats_server) as publisher:
        await publisher.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.ATTENTIVE,
                current=PresenceState.REFLECTIVE,
                reason="memory_candidate",
            ),
        )
        await publisher.flush()
        await asyncio.sleep(1.0)

    # Hit the cockpit's /api/now.
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{port}", timeout=5.0
    ) as client:
        r = await client.get("/api/now")
    assert r.status_code == 200
    body = r.json()
    assert body["state"]["current"] == "reflective"
    assert body["last_utterance"] is not None
    assert "yesterday" in body["last_utterance"]["text"].lower() or \
           "landing" in body["last_utterance"]["text"].lower()
    assert body["mood"]["palette"] == "reflective_violet"
    assert body["restraint"]["aired_total"] >= 1

    for s in services:
        s.shutdown()
    await asyncio.gather(*tasks, return_exceptions=True)
