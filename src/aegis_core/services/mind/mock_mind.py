"""mock_mind — Plan D stand-in for the real `mind` service.

Subscribes to state.changed; on entering REFLECTIVE, publishes one
UtteranceProposal from a configurable list of "recipes" in round-robin.
Used by the Plan D capstone to drive a noisy proposal stream through
the Steward without needing real cognition.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from ...bus import AegisBus
from ...messages import (
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from .._base import AegisService

log = structlog.get_logger()


@dataclass(frozen=True)
class ProposalRecipe:
    text: str
    intervention_class: InterventionClass
    weight: float
    confidence: float


class MockMindService(AegisService):
    name = "mind"

    def __init__(
        self,
        recipes: list[ProposalRecipe] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._recipes: list[ProposalRecipe] = list(recipes or [])
        self._cursor = 0
        self._bus: AegisBus | None = None

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        await bus.subscribe("state.changed", StateChanged, self._on_state)

    async def _on_state(self, msg: StateChanged) -> None:
        if (
            msg.current == PresenceState.REFLECTIVE
            and self._bus is not None
            and self._recipes
        ):
            recipe = self._recipes[self._cursor % len(self._recipes)]
            self._cursor += 1
            await self._bus.publish(
                "mind.utterance_proposal",
                UtteranceProposal(
                    timestamp=datetime.now(UTC),
                    text=recipe.text,
                    intervention_class=recipe.intervention_class,
                    weight=recipe.weight,
                    confidence=recipe.confidence,
                ),
            )


def make_service(**kwargs) -> MockMindService:
    return MockMindService(**kwargs)
