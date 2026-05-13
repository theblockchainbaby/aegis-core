"""Messages emitted by the memory layer (memory / keeper services).

Plan E defines `ContinuityCandidate` — emitted by KeeperService when a
tentative Moment promotes to consolidated. The `mind` service consumes
this as the seed for Memory Magic Moment proposals.
"""
from __future__ import annotations

from pydantic import Field

from ._base import AegisMessage
from .mind_events import InterventionClass


class ContinuityCandidate(AegisMessage):
    """Memory's "this might be worth speaking about" signal."""

    moment_id: str = Field(min_length=1)
    moment_summary: str = Field(min_length=1)
    themes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_class: InterventionClass
