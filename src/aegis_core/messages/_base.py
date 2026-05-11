"""Common base for all NATS message models.

Every message carries a timestamp so the observer (and post-hoc replay) can
reconstruct the timeline without relying on broker clock.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AegisMessage(BaseModel):
    """Base class — opt into strict validation, immutable after construction."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    timestamp: datetime = Field(description="UTC timestamp of the event")
