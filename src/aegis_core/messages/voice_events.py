"""Messages emitted by the `steward` service to the `voice` service.

Plan D publishes VoiceSpeak; Plan E's voice service consumes it.
"""
from __future__ import annotations

from pydantic import Field

from ._base import AegisMessage
from .mind_events import InterventionClass


class VoiceSpeak(AegisMessage):
    """`steward` → `voice`: an utterance that has cleared the gate."""

    text: str = Field(min_length=1)
    voice_persona: str = Field(default="desk_companion")
    intervention_class: InterventionClass
    weight: float = Field(ge=0.0)
