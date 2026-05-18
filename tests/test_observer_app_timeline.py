from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.services.observer.ring_buffer import BufferedEvent, EventRingBuffer


def _ev(subject: str, t: int) -> BufferedEvent:
    from datetime import timedelta

    return BufferedEvent(
        subject=subject,
        timestamp=datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC) + timedelta(minutes=t),
        payload={"n": t},
    )


@pytest.mark.asyncio
async def test_timeline_returns_recent_events(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    buf = EventRingBuffer(capacity=100)
    for i in range(20):
        buf.append(_ev("state.changed", i))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/timeline?limit=5")
    body = r.json()
    assert len(body["events"]) == 5
    assert [e["payload"]["n"] for e in body["events"]] == [15, 16, 17, 18, 19]


@pytest.mark.asyncio
async def test_timeline_filters_by_subjects(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    buf = EventRingBuffer(capacity=100)
    buf.append(_ev("state.changed", 0))
    buf.append(_ev("voice.speak", 1))
    buf.append(_ev("state.changed", 2))
    buf.append(_ev("mood.changed", 3))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get(
            "/api/timeline?subjects=state.changed,mood.changed"
        )
    body = r.json()
    subjects = {e["subject"] for e in body["events"]}
    assert subjects == {"state.changed", "mood.changed"}


@pytest.mark.asyncio
async def test_timeline_defaults_to_100(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    buf = EventRingBuffer(capacity=200)
    for i in range(150):
        buf.append(_ev("x.event", i))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/timeline")
    body = r.json()
    assert len(body["events"]) == 100
