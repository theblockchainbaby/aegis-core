"""Event ring buffer — capacity-limited in-memory recent-events store.

Pure logic. The observer service appends events as they arrive on the bus
and reads them out via the REST and SSE endpoints. Thread-safety is not
required in Plan F because the observer runs single-process / single-event-loop.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BufferedEvent:
    subject: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)


class EventRingBuffer:
    def __init__(self, capacity: int = 500) -> None:
        self._buf: deque[BufferedEvent] = deque(maxlen=capacity)

    def append(self, event: BufferedEvent) -> None:
        self._buf.append(event)

    def snapshot(self) -> list[BufferedEvent]:
        return list(self._buf)

    def recent(self, n: int) -> list[BufferedEvent]:
        if n <= 0:
            return []
        items = list(self._buf)
        return items[-n:]

    def filter_subjects(self, subjects: set[str]) -> list[BufferedEvent]:
        return [e for e in self._buf if e.subject in subjects]

    def __len__(self) -> int:
        return len(self._buf)
