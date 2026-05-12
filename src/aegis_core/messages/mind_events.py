"""Messages emitted by the `mind` service.

Plan D defines only `UtteranceProposal` — the proposal-to-Steward contract.
The four intervention classes match spec §6 intervention_weights keys.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from ._base import AegisMessage


class InterventionClass(StrEnum):
    AMBIENT_NOTE = "ambient_note"
    ROUTINE_CONTINUITY = "routine_continuity"
    MEMORY_MAGIC = "memory_magic"
    EMOTIONAL_CHECK = "emotional_check"


class UtteranceProposal(AegisMessage):
    """`mind` proposes; Steward gates."""

    text: str = Field(min_length=1)
    intervention_class: InterventionClass
    weight: float = Field(ge=0.0, le=10.0)
    confidence: float = Field(ge=0.0, le=1.0)
    context: dict[str, Any] = Field(default_factory=dict)
