"""Messages emitted by the `senses` service.

Plan A defines only `PresenceObserved` — enough to drive the heartbeat
demo. Other sense events (voice activity, posture, scene tokens) land in
Plan B when the senses service is built out.
"""
from typing import Literal

from pydantic import Field

from ._base import AegisMessage


class PresenceObserved(AegisMessage):
    """Person-present signal from a perception source."""

    present: bool
    source: Literal["mmwave", "camera", "audio_vad"]
    confidence: float = Field(ge=0.0, le=1.0)
