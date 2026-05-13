from datetime import UTC, datetime

from aegis_core.services.observer.ring_buffer import BufferedEvent, EventRingBuffer


def _ev(subject: str, t: int = 0) -> BufferedEvent:
    return BufferedEvent(
        subject=subject,
        timestamp=datetime(2026, 5, 12, 9, t, 0, tzinfo=UTC),
        payload={"sample": True, "n": t},
    )


def test_buffer_records_events_in_insertion_order():
    buf = EventRingBuffer(capacity=10)
    buf.append(_ev("state.changed", 0))
    buf.append(_ev("voice.speak", 1))
    items = buf.snapshot()
    assert [e.subject for e in items] == ["state.changed", "voice.speak"]


def test_buffer_evicts_oldest_when_at_capacity():
    buf = EventRingBuffer(capacity=3)
    for i in range(5):
        buf.append(_ev("x.event", i))
    items = buf.snapshot()
    assert len(items) == 3
    assert [e.payload["n"] for e in items] == [2, 3, 4]


def test_recent_returns_last_n_in_order():
    buf = EventRingBuffer(capacity=10)
    for i in range(6):
        buf.append(_ev("x.event", i))
    last3 = buf.recent(3)
    assert [e.payload["n"] for e in last3] == [3, 4, 5]


def test_filter_by_subject():
    buf = EventRingBuffer(capacity=10)
    buf.append(_ev("state.changed", 0))
    buf.append(_ev("voice.speak", 1))
    buf.append(_ev("state.changed", 2))
    filtered = buf.filter_subjects({"state.changed"})
    assert all(e.subject == "state.changed" for e in filtered)
    assert len(filtered) == 2
