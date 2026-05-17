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
    source: Literal["mmwave", "camera", "audio_vad", "host_input"]
    confidence: float = Field(ge=0.0, le=1.0)


class VoiceActivityDetected(AegisMessage):
    """Frame-level voice activity decision from the VAD detector."""

    active: bool
    rms_db: float
    confidence: float = Field(ge=0.0, le=1.0)


class PostureObserved(AegisMessage):
    """Coarse posture / engagement read from the camera."""

    at_desk: bool
    gaze: Literal["screen", "away", "absent"]
    movement_score: float = Field(ge=0.0, le=1.0)


class AmbientLightReading(AegisMessage):
    """Lux reading from the ambient-light sensor."""

    lux: float = Field(ge=0.0)


class ThermalReading(AegisMessage):
    """Compute-exhaust temperature reading."""

    celsius: float
