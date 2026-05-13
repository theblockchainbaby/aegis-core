"""Messages emitted by the `mood` service.

Plan E defines `MoodChanged` — palette + breath cadence + warmth.
Downstream consumers (Plan A's MCU heartbeat, Plan F's observer cockpit)
render these events; Plan E only publishes them.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from ._base import AegisMessage


class Palette(StrEnum):
    """The seven palettes tracked by Plan B's Presence State Machine."""

    SLEEP = "sleep"
    DORMANT_BLUE = "dormant_blue"
    OBSERVING_DRIFT = "observing_drift"
    ATTENTIVE_WARM = "attentive_warm"
    SETTLING_REGRESS = "settling_regress"
    REFLECTIVE_VIOLET = "reflective_violet"
    QUIET_COOL = "quiet_cool"


class MoodChanged(AegisMessage):
    """The mood service's primary output."""

    palette: Palette
    breath_cadence_seconds: float = Field(ge=0.5, le=20.0)
    warmth: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
