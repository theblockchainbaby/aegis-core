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
