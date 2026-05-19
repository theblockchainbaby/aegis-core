"""FastAPI app factory for the observer service.

The factory accepts the ring buffer + db_path so tests can inject mocks
and the service can wire production resources at startup. No global
state.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ring_buffer import BufferedEvent, EventRingBuffer


def build_app(
    *,
    buffer: EventRingBuffer,
    db_path: str | Path,
) -> FastAPI:
    app = FastAPI(title="Aegis Core Observer", version="0.1.0")
    app.state.buffer = buffer
    app.state.db_path = Path(db_path)
    app.state.bus = None

    here = Path(__file__).resolve().parent
    app.mount(
        "/static",
        StaticFiles(directory=str(here / "static")),
        name="static",
    )
    templates = Jinja2Templates(directory=str(here / "templates"))
    app.state.templates = templates
    app.state.sse_queues: list[asyncio.Queue] = []

    @app.get("/sse/events")
    async def sse_events() -> StreamingResponse:
        async def stream() -> AsyncIterator[bytes]:
            q: asyncio.Queue = asyncio.Queue(maxsize=200)
            app.state.sse_queues.append(q)
            try:
                while True:
                    event: BufferedEvent = await q.get()
                    payload = {
                        "subject": event.subject,
                        "timestamp": event.timestamp.isoformat(),
                        "payload": event.payload,
                    }
                    yield f"data: {json.dumps(payload)}\n\n".encode()
            finally:
                try:
                    app.state.sse_queues.remove(q)
                except ValueError:
                    pass

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/healthz")
    def healthz() -> JSONResponse:
        bus = app.state.bus
        if bus is not None and not bus.is_connected:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "bus": "disconnected"},
            )
        return JSONResponse(status_code=200, content={"status": "ok"})

    @app.get("/api/now")
    def api_now() -> dict:
        buffer: EventRingBuffer = app.state.buffer
        db_path = app.state.db_path

        def _last(subject: str) -> dict | None:
            matches = buffer.filter_subjects({subject})
            return matches[-1].payload if matches else None

        latest_state = _last("state.changed")
        latest_mood = _last("mood.changed")
        latest_utterance = _last("voice.speak")
        latest_candidate = _last("memory.continuity_candidate")

        # Read intervention counts from the DB (if it exists).
        from ...storage._conn import connect
        from ...storage.interventions import InterventionStore
        from ...storage.schema import run_migrations

        restraint = {"aired_total": 0, "vetoed_total": 0}
        if db_path.exists():
            conn = connect(db_path)
            try:
                run_migrations(conn)
                store = InterventionStore(conn)
                restraint["aired_total"] = store.count_aired()
                restraint["vetoed_total"] = store.count_vetoed()
            finally:
                conn.close()

        return {
            "state": latest_state,
            "mood": latest_mood,
            "last_utterance": latest_utterance,
            "last_candidate": latest_candidate,
            "restraint": restraint,
        }

    @app.get("/api/timeline")
    def api_timeline(
        limit: int = 100,
        subjects: str | None = None,
    ) -> dict:
        buffer: EventRingBuffer = app.state.buffer
        if subjects:
            wanted = {s.strip() for s in subjects.split(",") if s.strip()}
            items = buffer.filter_subjects(wanted)
            items = items[-limit:]
        else:
            items = buffer.recent(limit)

        return {
            "events": [
                {
                    "subject": e.subject,
                    "timestamp": e.timestamp.isoformat(),
                    "payload": e.payload,
                }
                for e in items
            ]
        }

    @app.get("/api/snapshots/{date_str}")
    def api_snapshot_for_date(date_str: str) -> dict:
        from datetime import date as _date

        from ...storage._conn import connect
        from ...storage.schema import run_migrations
        from .snapshots import generate_daily_snapshot

        d = _date.fromisoformat(date_str)
        db_path = app.state.db_path
        if not db_path.exists():
            return {
                "date": date_str,
                "interventions": {"aired": 0, "vetoed": 0},
            }
        conn = connect(db_path)
        try:
            run_migrations(conn)
            return generate_daily_snapshot(d, conn)
        finally:
            conn.close()

    @app.get("/api/dogfood")
    def api_dogfood() -> dict:
        from ...storage._conn import connect
        from ...storage.interventions import InterventionStore
        from ...storage.schema import run_migrations
        from .dogfood import compute_dogfood_state

        db_path = app.state.db_path
        if not db_path.exists():
            return {
                "day_of_90": 0,
                "started_at": None,
                "aired_total": 0,
                "vetoed_total": 0,
            }
        conn = connect(db_path)
        try:
            run_migrations(conn)
            state = compute_dogfood_state(conn)
            store = InterventionStore(conn)
            return {
                "day_of_90": state.day_of_90,
                "started_at": (
                    state.started_at.isoformat() if state.started_at else None
                ),
                "aired_total": store.count_aired(),
                "vetoed_total": store.count_vetoed(),
            }
        finally:
            conn.close()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        # Reuse the api_now logic.
        now = api_now()
        dogfood = api_dogfood()
        events = [
            {
                "subject": e.subject,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in app.state.buffer.recent(50)
        ]
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "state": now["state"],
                "mood": now["mood"],
                "last_utterance": now["last_utterance"],
                "last_candidate": now["last_candidate"],
                "restraint": now["restraint"],
                "events": events,
                "dogfood": dogfood,
            },
        )

    return app


async def broadcast_event(app, event: BufferedEvent) -> None:
    """Push event to all SSE-connected clients. Service calls this from
    the bus subscriber callbacks (Task 8 wires that)."""
    for q in list(app.state.sse_queues):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Slow consumer; drop.
            pass
