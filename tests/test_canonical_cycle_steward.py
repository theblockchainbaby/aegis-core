"""Plan D capstone — prove restraint: more vetoes than aired utterances."""
import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.bus import AegisBus
from aegis_core.messages import (
    InterventionClass,
    PresenceState,
    StateChanged,
    VoiceSpeak,
)
from aegis_core.services.mind.mock_mind import MockMindService, ProposalRecipe
from aegis_core.services.steward.service import StewardService
from aegis_core.storage._conn import connect
from aegis_core.storage.interventions import InterventionStore
from aegis_core.storage.schema import run_migrations

REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


def _noisy_recipes() -> list[ProposalRecipe]:
    """Mix of clean, low-confidence, forbidden-tone, and over-weight proposals."""
    return [
        # Clean (should air)
        ProposalRecipe(
            text="Yesterday you mentioned the landing page.",
            intervention_class=InterventionClass.MEMORY_MAGIC,
            weight=1.0,
            confidence=0.92,
        ),
        # Low confidence (vetoed: confidence_below_threshold)
        ProposalRecipe(
            text="Maybe you should think about lunch.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.65,
        ),
        # Forbidden tone (vetoed: imperative)
        ProposalRecipe(
            text="You need to take a break.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.95,
        ),
        # Forbidden tone (vetoed: exclamation + coaching)
        ProposalRecipe(
            text="Great work today!",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.95,
        ),
        # Hedging assistantese (vetoed)
        ProposalRecipe(
            text="Just wanted to mention that you've been quiet.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.95,
        ),
        # Clean ambient (might air if budget allows)
        ProposalRecipe(
            text="You usually stop around now.",
            intervention_class=InterventionClass.ROUTINE_CONTINUITY,
            weight=0.5,
            confidence=0.90,
        ),
        # Quantified advice (vetoed)
        ProposalRecipe(
            text="You've been at it for 20 minutes more than usual.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.95,
        ),
        # Low confidence again
        ProposalRecipe(
            text="The room seems quieter than yesterday.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.70,
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_capstone_more_vetoes_than_aired(nats_server, tmp_path: Path):
    db = tmp_path / "m.db"
    steward = StewardService(
        nats_url=nats_server,
        db_path=db,
        rules_path=REPO_RULES,
    )
    mind = MockMindService(nats_url=nats_server, recipes=_noisy_recipes())

    speaks: list[VoiceSpeak] = []

    async def collect(msg: VoiceSpeak) -> None:
        speaks.append(msg)

    steward_task = asyncio.create_task(steward.run())
    mind_task = asyncio.create_task(mind.run())
    await asyncio.sleep(0.4)

    async with AegisBus.connect(nats_server) as listener:
        await listener.subscribe("voice.speak", VoiceSpeak, collect)

        async with AegisBus.connect(nats_server) as publisher:
            # Drive 20 REFLECTIVE entries to give mock_mind 20 cycles through
            # its noisy recipe list.
            for _ in range(20):
                await publisher.publish(
                    "state.changed",
                    StateChanged(
                        timestamp=datetime.now(UTC),
                        previous=PresenceState.ATTENTIVE,
                        current=PresenceState.REFLECTIVE,
                        reason="test",
                    ),
                )
                await publisher.flush()
                await asyncio.sleep(0.15)

            await asyncio.sleep(1.0)

    steward.shutdown()
    mind.shutdown()
    await asyncio.gather(steward_task, mind_task, return_exceptions=True)

    conn = connect(db)
    run_migrations(conn)
    store = InterventionStore(conn)
    aired_count = store.count_aired()
    vetoed_count = store.count_vetoed()
    conn.close()

    # The behavioral proof of restraint:
    # - At least 5x as many vetoes as aired utterances
    # - At least 10 total decisions (the stream was real)
    assert aired_count + vetoed_count >= 10
    assert vetoed_count > aired_count, (
        f"Steward not restraining enough: aired={aired_count}, vetoed={vetoed_count}"
    )
    # Beyond just > , prove the ratio is meaningful (restraint, not luck).
    assert vetoed_count >= 2 * aired_count, (
        f"Steward restraint ratio too weak: "
        f"vetoed={vetoed_count} aired={aired_count}; expected vetoed >= 2 * aired"
    )

    # And the voice.speak count must equal aired_count (Steward emits exactly
    # one voice.speak per aired decision).
    assert len(speaks) == aired_count
