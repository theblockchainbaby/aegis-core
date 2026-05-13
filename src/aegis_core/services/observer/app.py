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

    return app
