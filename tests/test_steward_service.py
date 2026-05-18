import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from aegis_core.services.steward.service import StewardService
from aegis_core.storage._conn import connect
from aegis_core.storage.interventions import InterventionStore
from aegis_core.storage.schema import run_migrations

REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_steward_logs_proposal_decision(nats_server, tmp_path: Path):
    db_path = tmp_path / "m.db"
    service = StewardService(
        nats_url=nats_server,
        db_path=db_path,
        rules_path=REPO_RULES,
    )
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as publisher:
        # Put state into Reflective first.
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
        await asyncio.sleep(0.2)

        # Now publish a clean proposal.
        await publisher.publish(
            "mind.utterance_proposal",
            UtteranceProposal(
                timestamp=datetime.now(UTC),
                text="Yesterday you mentioned the landing page.",
                intervention_class=InterventionClass.MEMORY_MAGIC,
                weight=1.0,
                confidence=0.92,
            ),
        )
        await publisher.flush()
        await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    conn = connect(db_path)
    run_migrations(conn)
    rows = InterventionStore(conn).query_all()
    conn.close()

    # In skeleton (Task 9), Steward logs the decision. The decision should be
    # 'aired' for this clean proposal since it passed the gate.
    assert len(rows) == 1
    assert rows[0]["decision"] == "aired"
    assert rows[0]["text"] == "Yesterday you mentioned the landing page."


from aegis_core.messages import VoiceSpeak


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_aired_proposal_publishes_voice_speak(nats_server, tmp_path: Path):
    db_path = tmp_path / "m.db"
    service = StewardService(
        nats_url=nats_server,
        db_path=db_path,
        rules_path=REPO_RULES,
    )
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    speaks: list[VoiceSpeak] = []

    async def collect(msg: VoiceSpeak) -> None:
        speaks.append(msg)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("voice.speak", VoiceSpeak, collect)
        await listener.flush()

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
            await publisher.publish(
                "mind.utterance_proposal",
                UtteranceProposal(
                    timestamp=datetime.now(UTC),
                    text="Yesterday you mentioned the landing page.",
                    intervention_class=InterventionClass.MEMORY_MAGIC,
                    weight=1.0,
                    confidence=0.92,
                ),
            )
            await publisher.flush()
            await asyncio.sleep(0.5)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    assert len(speaks) == 1
    assert speaks[0].intervention_class == InterventionClass.MEMORY_MAGIC
    assert "landing page" in speaks[0].text
