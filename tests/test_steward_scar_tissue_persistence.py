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
from aegis_core.storage.scar_tissue import ScarTissueStore
from aegis_core.storage.schema import run_migrations


REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_veto_bumps_scar_tissue(nats_server, tmp_path: Path):
    db = tmp_path / "m.db"
    service = StewardService(
        nats_url=nats_server, db_path=db, rules_path=REPO_RULES
    )
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as p:
        # Stay in OBSERVING (wrong state for speech) so the proposal is vetoed.
        await p.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.DORMANT,
                current=PresenceState.OBSERVING,
                reason="t",
            ),
        )
        await p.publish(
            "mind.utterance_proposal",
            UtteranceProposal(
                timestamp=datetime.now(UTC),
                text="x",
                intervention_class=InterventionClass.AMBIENT_NOTE,
                weight=0.1,
                confidence=0.95,
            ),
        )
        await p.flush()
        await asyncio.sleep(0.4)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    conn = connect(db)
    run_migrations(conn)
    pen = ScarTissueStore(conn).get_penalty("ambient_note")
    conn.close()
    assert pen > 0.0


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_settling_after_aired_recovers_scar_tissue(
    nats_server, tmp_path: Path
):
    db = tmp_path / "m.db"
    # Pre-seed scar tissue so we can verify it goes down.
    conn = connect(db)
    run_migrations(conn)
    ScarTissueStore(conn).bump_veto("memory_magic", by=0.06)
    conn.close()

    service = StewardService(
        nats_url=nats_server, db_path=db, rules_path=REPO_RULES
    )
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.3)

    async with AegisBus.connect(nats_server) as p:
        # Reflective → aired utterance → Settling (treated as ack).
        await p.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.ATTENTIVE,
                current=PresenceState.REFLECTIVE,
                reason="t",
            ),
        )
        await p.publish(
            "mind.utterance_proposal",
            UtteranceProposal(
                timestamp=datetime.now(UTC),
                text="Yesterday you mentioned the landing page.",
                intervention_class=InterventionClass.MEMORY_MAGIC,
                weight=1.0,
                confidence=0.95,
            ),
        )
        await p.flush()
        await asyncio.sleep(0.3)
        await p.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.REFLECTIVE,
                current=PresenceState.SETTLING,
                reason="reflective_done",
            ),
        )
        await p.flush()
        await asyncio.sleep(0.3)

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)

    conn = connect(db)
    pen = ScarTissueStore(conn).get_penalty("memory_magic")
    conn.close()
    # We pre-seeded 0.06; the ack should subtract 0.07 → floored to 0.0.
    assert pen == 0.0
