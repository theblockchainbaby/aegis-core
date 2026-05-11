"""Messages emitted by the `state` service.

Per spec §5: seven presence states with minimum dwell times. The `state`
service is the sole owner of these transitions and publishes a single
StateChanged event per transition.
"""
from enum import StrEnum

from pydantic import Field

from ._base import AegisMessage


class PresenceState(StrEnum):
    SLEEP = "sleep"
    DORMANT = "dormant"
    OBSERVING = "observing"
    ATTENTIVE = "attentive"
    SETTLING = "settling"
    REFLECTIVE = "reflective"
    QUIET = "quiet"


class StateChanged(AegisMessage):
    """Emitted on every presence-state transition."""

    previous: PresenceState
    current: PresenceState
    reason: str = Field(description="Short human-readable reason for the transition")
