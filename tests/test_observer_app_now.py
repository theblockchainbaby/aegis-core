"""Skeleton smoke tests; Task 4 extends with /api/now assertions."""
from pathlib import Path

import pytest


def test_app_constructs_without_args(tmp_path: Path):
    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer

    app = build_app(
        buffer=EventRingBuffer(capacity=50),
        db_path=tmp_path / "m.db",
    )
    assert app is not None


@pytest.mark.asyncio
async def test_healthz_returns_ok(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer

    app = build_app(
        buffer=EventRingBuffer(capacity=50),
        db_path=tmp_path / "m.db",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


from datetime import UTC, datetime

from aegis_core.services.observer.ring_buffer import BufferedEvent


@pytest.mark.asyncio
async def test_api_now_returns_latest_state_and_mood(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer

    buf = EventRingBuffer(capacity=50)
    # Latest state event
    buf.append(BufferedEvent(
        subject="state.changed",
        timestamp=datetime(2026, 5, 12, 9, 14, 0, tzinfo=UTC),
        payload={
            "previous": "dormant", "current": "attentive",
            "reason": "engagement", "timestamp": "2026-05-12T09:14:00+00:00",
        },
    ))
    # Latest mood
    buf.append(BufferedEvent(
        subject="mood.changed",
        timestamp=datetime(2026, 5, 12, 9, 14, 1, tzinfo=UTC),
        payload={
            "palette": "attentive_warm", "breath_cadence_seconds": 5.5,
            "warmth": 0.7, "reason": "state_attentive",
            "timestamp": "2026-05-12T09:14:01+00:00",
        },
    ))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/now")
    assert r.status_code == 200
    body = r.json()
    assert body["state"]["current"] == "attentive"
    assert body["mood"]["palette"] == "attentive_warm"
    assert body["mood"]["warmth"] == 0.7


@pytest.mark.asyncio
async def test_api_now_returns_latest_utterance_and_candidate(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer

    buf = EventRingBuffer(capacity=50)
    buf.append(BufferedEvent(
        subject="memory.continuity_candidate",
        timestamp=datetime.now(UTC),
        payload={
            "moment_id": "moment_abc",
            "moment_summary": "Landing page redesign session.",
            "themes": ["landing"],
            "confidence": 0.9,
            "suggested_class": "memory_magic",
            "timestamp": "2026-05-12T09:14:00+00:00",
        },
    ))
    buf.append(BufferedEvent(
        subject="voice.speak",
        timestamp=datetime.now(UTC),
        payload={
            "text": "Yesterday you mentioned the landing.",
            "voice_persona": "desk_companion",
            "intervention_class": "memory_magic",
            "weight": 1.0,
            "timestamp": "2026-05-12T09:14:30+00:00",
        },
    ))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/now")
    assert r.status_code == 200
    body = r.json()
    assert "Yesterday you mentioned" in body["last_utterance"]["text"]
    assert body["last_candidate"]["moment_id"] == "moment_abc"


@pytest.mark.asyncio
async def test_api_now_returns_intervention_counts_from_db(tmp_path: Path):
    """Counts come from InterventionStore — seeded directly in this test."""
    import httpx

    from aegis_core.services.observer.app import build_app
    from aegis_core.services.observer.ring_buffer import EventRingBuffer
    from aegis_core.storage._conn import connect
    from aegis_core.storage.interventions import InterventionStore
    from aegis_core.storage.schema import run_migrations

    db = tmp_path / "m.db"
    conn = connect(db)
    run_migrations(conn)
    store = InterventionStore(conn)
    for _ in range(3):
        store.log_aired(
            timestamp=datetime.now(UTC),
            intervention_class="memory_magic",
            weight=1.0,
            confidence=0.92,
            text="x",
        )
    for _ in range(11):
        store.log_vetoed(
            timestamp=datetime.now(UTC),
            intervention_class="ambient_note",
            weight=0.1,
            confidence=0.4,
            text="x",
            reasons=["confidence_below_threshold"],
        )
    conn.close()

    app = build_app(buffer=EventRingBuffer(capacity=50), db_path=db)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/api/now")
    body = r.json()
    assert body["restraint"]["aired_total"] == 3
    assert body["restraint"]["vetoed_total"] == 11
