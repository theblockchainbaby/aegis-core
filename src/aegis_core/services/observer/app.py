"""FastAPI app factory for the observer service.

The factory accepts the ring buffer + db_path so tests can inject mocks
and the service can wire production resources at startup. No global
state.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from .ring_buffer import EventRingBuffer


def build_app(
    *,
    buffer: EventRingBuffer,
    db_path: str | Path,
) -> FastAPI:
    app = FastAPI(title="Aegis Core Observer", version="0.1.0")
    app.state.buffer = buffer
    app.state.db_path = Path(db_path)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app
