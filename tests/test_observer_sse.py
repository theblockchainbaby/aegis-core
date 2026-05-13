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
