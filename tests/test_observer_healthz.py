from pathlib import Path

import pytest

from aegis_core.services.observer.ring_buffer import EventRingBuffer


class _FakeBus:
    """Stands in for AegisBus. Only needs the is_connected property."""

    def __init__(self, connected: bool) -> None:
        self._connected = connected

    @property
    def is_connected(self) -> bool:
        return self._connected


@pytest.mark.asyncio
async def test_healthz_unhealthy_when_bus_disconnected(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    app = build_app(buffer=EventRingBuffer(capacity=10), db_path=tmp_path / "m.db")
    app.state.bus = _FakeBus(connected=False)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/healthz")
    assert r.status_code == 503
    assert r.json()["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_healthz_ok_when_bus_connected(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    app = build_app(buffer=EventRingBuffer(capacity=10), db_path=tmp_path / "m.db")
    app.state.bus = _FakeBus(connected=True)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_healthz_ok_when_no_bus_wired(tmp_path: Path):
    import httpx

    from aegis_core.services.observer.app import build_app

    # A freshly built app has no bus attached. That is not a failure to
    # report; nothing has gone wrong, the bus is simply not wired yet.
    app = build_app(buffer=EventRingBuffer(capacity=10), db_path=tmp_path / "m.db")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_aegis_bus_reports_connected(nats_server):
    from aegis_core.bus import AegisBus

    async with AegisBus.connect(nats_server) as bus:
        assert bus.is_connected is True
