"""Source protocol — every sensor adapter implements this.

A Source is an async iterator of (subject, message) pairs. The `senses`
service consumes from many sources concurrently and publishes each message
to the NATS bus on the named subject. Sources own their own pacing — they
can yield as fast as their sensor produces, or at a fixed cadence.

Real sources read from hardware (camera, mic, mmWave, I²C). Mock sources
replay recorded fixtures. The protocol is identical, which is what makes
mock-first testing honest.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ....messages._base import AegisMessage


@runtime_checkable
class Source(Protocol):
    """A streaming sensor source."""

    name: str
    """Short identifier used in logs and the trace format."""

    def events(self) -> AsyncIterator[tuple[str, AegisMessage]]:
        """Yield (subject, message) pairs forever (or until exhausted)."""
        ...

    async def aclose(self) -> None:
        """Release any resources (file handles, hardware connections)."""
        ...
