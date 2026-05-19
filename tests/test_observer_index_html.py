from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.services.observer.ring_buffer import BufferedEvent, EventRingBuffer


@pytest.mark.asyncio
async def test_index_page_renders(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    app = build_app(
        buffer=EventRingBuffer(capacity=50),
        db_path=tmp_path / "m.db",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Aegis Core" in body
    # Should NOT contain analytics-ish words (spec §10.2 forbids streaks/scores).
    assert "streak" not in body.lower()
    assert "score" not in body.lower() or "focus_score" in body.lower()


@pytest.mark.asyncio
async def test_index_page_renders_current_state_when_present(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    buf = EventRingBuffer(capacity=50)
    buf.append(BufferedEvent(
        subject="state.changed",
        timestamp=datetime(2026, 5, 12, 9, 14, 0, tzinfo=UTC),
        payload={
            "previous": "dormant", "current": "attentive",
            "reason": "engagement", "timestamp": "2026-05-12T09:14:00+00:00",
        },
    ))

    app = build_app(buffer=buf, db_path=tmp_path / "m.db")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/")
    assert "attentive" in r.text.lower()


@pytest.mark.asyncio
async def test_index_exposes_live_now_panel_ids(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    app = build_app(
        buffer=EventRingBuffer(capacity=50),
        db_path=tmp_path / "m.db",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/")
    body = r.text
    # app.js targets these ids to update the Now panel live over SSE.
    assert 'id="presence-value"' in body
    assert 'id="mood-value"' in body


@pytest.mark.asyncio
async def test_static_css_serves(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    app = build_app(
        buffer=EventRingBuffer(capacity=50),
        db_path=tmp_path / "m.db",
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
