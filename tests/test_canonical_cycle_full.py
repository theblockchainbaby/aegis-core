"""Plan E capstone — full chain produces one utterance + one mood shift."""
import asyncio
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    InterventionClass,
    MoodChanged,
    PresenceState,
    StateChanged,
    VoiceSpeak,
)
from aegis_core.services.keeper.service import KeeperService
from aegis_core.services.mind.service import MindService
from aegis_core.services.mood.service import MoodService
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


@pytest.mark.asyncio
@pytest.mark.timeout(45)
async def test_capstone_one_utterance_and_one_mood_shift(
    nats_server, tmp_path: Path
):
    db_path = tmp_path / "m.db"
    moment_id = _seed_consolidatable_moment(db_path)

    speaks: list[VoiceSpeak] = []
    moods: list[MoodChanged] = []

    async def collect_speak(msg: VoiceSpeak) -> None:
        speaks.append(msg)

    async def collect_mood(msg: MoodChanged) -> None:
        moods.append(msg)

    # Bring up the four real services + keeper for consolidation.
    voice_buf = io.StringIO()
    voice = VoiceService(
        nats_url=nats_server,
        backend=StdoutBackend(stream=voice_buf, log_path=tmp_path / "voice.log"),
    )
    mind = MindService(nats_url=nats_server, db_path=db_path)
    steward = StewardService(
        nats_url=nats_server, db_path=db_path, rules_path=REPO_RULES
    )
    mood = MoodService(nats_url=nats_server)
    keeper = KeeperService(db_path=db_path)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("voice.speak", VoiceSpeak, collect_speak)
        await listener.subscribe("mood.changed", MoodChanged, collect_mood)

        tasks = [
            asyncio.create_task(voice.run()),
            asyncio.create_task(mind.run()),
            asyncio.create_task(steward.run()),
            asyncio.create_task(mood.run()),
        ]
        await asyncio.sleep(0.5)

        # Use keeper to consolidate + publish ContinuityCandidate.
        async with AegisBus.connect(nats_server) as keeper_bus:
            keeper._open_db()
            keeper._bus = keeper_bus
            counts = await keeper.consolidate_now_async()
            assert counts["consolidated"] == 1
            await keeper_bus.flush()
            await asyncio.sleep(0.3)

        # Drive REFLECTIVE state.
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
            await asyncio.sleep(0.8)

        voice.shutdown()
        mind.shutdown()
        steward.shutdown()
        mood.shutdown()
        await asyncio.gather(*tasks, return_exceptions=True)

    # The capstone assertion: exactly one printable utterance.
    assert len(speaks) == 1, f"expected exactly 1 utterance, got {len(speaks)}: {[s.text for s in speaks]}"
    assert speaks[0].intervention_class == InterventionClass.MEMORY_MAGIC
    assert "yesterday" in speaks[0].text.lower() or "landing" in speaks[0].text.lower()

    # And the StdoutBackend printed it.
    assert speaks[0].text in voice_buf.getvalue()

    # And at least one mood shift (the REFLECTIVE state change emits one).
    assert len(moods) >= 1
    reflective_moods = [
        m for m in moods if m.reason == "state_reflective"
    ]
    assert len(reflective_moods) >= 1
