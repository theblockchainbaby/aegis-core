import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.services.observer.app import build_app, broadcast_event
from aegis_core.services.observer.ring_buffer import BufferedEvent, EventRingBuffer



@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_sse_delivers_pushed_event(tmp_path: Path):
    import httpx
    import uvicorn

    buf = EventRingBuffer(capacity=50)
    app = build_app(buffer=buf, db_path=tmp_path / "m.db")

    # Run a real uvicorn server on a free port so the infinite SSE stream
    # works concurrently with the broadcaster (httpx.ASGITransport awaits
    # the entire ASGI app to completion and cannot handle infinite streams).
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Wait for uvicorn to report started and bind its port.
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.05)
    assert server.started, "uvicorn did not start in time"

    # Discover the bound port.
    port = server.servers[0].sockets[0].getsockname()[1]

    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=5.0) as client:
            # Open the SSE connection.
            async with client.stream("GET", "/sse/events") as resp:
                assert resp.status_code == 200

                # Push an event into the broadcaster concurrently.
                async def _push():
                    # Brief yield so the SSE generator has registered its queue.
                    await asyncio.sleep(0.05)
                    await broadcast_event(
                        app,
                        BufferedEvent(
                            subject="state.changed",
                            timestamp=datetime.now(UTC),
                            payload={"current": "attentive"},
                        ),
                    )

                push_task = asyncio.create_task(_push())

                # Read at least one SSE frame.
                async for chunk in resp.aiter_text():
                    if "state.changed" in chunk:
                        break

                await push_task
    finally:
        server.should_exit = True
        await server_task


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_service_publishes_to_sse_on_bus_event(nats_server, tmp_path: Path):
    """The full chain: bus → observer service → ring buffer → SSE → client."""
    import httpx
    from aegis_core.bus import AegisBus
    from aegis_core.messages import PresenceState, StateChanged
    from aegis_core.services.observer.service import ObserverService

    # Spin up the service on a random port.
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    service = ObserverService(
        nats_url=nats_server,
        host="127.0.0.1",
        port=port,
        db_path=tmp_path / "m.db",
    )
    task = asyncio.create_task(service.run())
    # Wait for uvicorn to bind.
    await asyncio.sleep(0.6)

    received_lines: list[str] = []
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{port}", timeout=5.0
    ) as client:
        async with client.stream("GET", "/sse/events") as resp:
            assert resp.status_code == 200

            async def reader() -> None:
                async for line in resp.aiter_lines():
                    received_lines.append(line)
                    if any("state.changed" in l for l in received_lines):
                        break

            read_task = asyncio.create_task(reader())
            # Now publish a real bus event.
            await asyncio.sleep(0.2)
            async with AegisBus.connect(nats_server) as publisher:
                await publisher.publish(
                    "state.changed",
                    StateChanged(
                        timestamp=datetime.now(UTC),
                        previous=PresenceState.DORMANT,
                        current=PresenceState.OBSERVING,
                        reason="t",
                    ),
                )
                await publisher.flush()
            await asyncio.wait_for(read_task, timeout=8.0)

    service.shutdown()
    await asyncio.wait_for(task, timeout=8.0)

    assert any("state.changed" in l for l in received_lines)
