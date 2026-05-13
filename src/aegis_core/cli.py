"""aegis-core CLI.

Dev-only. On the Jetson, services are managed by systemd (see ops/systemd/).
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

import click
import structlog

from .bus import AegisBus
from .services import (
    heartbeat,
    keeper,
    memory,
    mind,
    mood,
    observer,
    senses,
    state,
    steward,
    voice,
)

log = structlog.get_logger()

SERVICE_FACTORIES = {
    "senses": senses.make_service,
    "state": state.make_service,
    "memory": memory.make_service,
    "mood": mood.make_service,
    "mind": mind.make_service,
    "steward": steward.make_service,
    "voice": voice.make_service,
    "observer": observer.make_service,
    "keeper": keeper.make_service,
    "heartbeat": heartbeat.make_service,
}


@click.group()
def main() -> None:
    """aegis-core dev CLI."""


@main.command()
@click.option("--nats-url", default="nats://127.0.0.1:4222")
def up(nats_url: str) -> None:
    """Spawn local NATS + all service stubs."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    nats_conf = repo_root / "ops" / "natsconfig" / "nats.conf"
    nats_proc = subprocess.Popen(
        ["nats-server", "-c", str(nats_conf)],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    click.echo(f"NATS server started (pid={nats_proc.pid})")

    async def run_all() -> None:
        services = [factory(nats_url=nats_url) for factory in SERVICE_FACTORIES.values()]
        tasks = [asyncio.create_task(s.run()) for s in services]

        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await stop.wait()

        for s in services:
            s.shutdown()
        await asyncio.gather(*tasks, return_exceptions=True)

    try:
        asyncio.run(run_all())
    finally:
        nats_proc.terminate()
        try:
            nats_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            nats_proc.kill()
        click.echo("aegis-core stopped")


@main.command()
@click.option("--nats-url", default="nats://127.0.0.1:4222")
@click.option("--service", default=None, help="Ping only one service (default: all).")
def ping(nats_url: str, service: str | None) -> None:
    """Ping the bus and report which services answer."""
    targets = [service] if service else list(SERVICE_FACTORIES)

    async def run() -> None:
        replies: dict[str, str] = {}

        async with AegisBus.connect(nats_url) as bus:
            async def collect(raw):
                replies[raw.subject.split(".")[-1]] = raw.data.decode()

            for name in targets:
                await bus._nc.subscribe(f"ping.reply.{name}", cb=collect)
            await bus.flush()
            for name in targets:
                await bus._nc.publish("ping.request", name.encode())
            await bus.flush()
            await asyncio.sleep(0.5)

        for name in targets:
            click.echo(f"{name:10s} {replies.get(name, 'NO REPLY')}")

    asyncio.run(run())


@main.group()
def trace() -> None:
    """Trace replay tools — drive Aegis Core from a fixture."""


@trace.command("replay")
@click.argument("fixture_path", type=click.Path(exists=True))
@click.option("--nats-url", default="nats://127.0.0.1:4222")
@click.option(
    "--real-time/--fast",
    default=False,
    help="Real-time honors recorded offsets; --fast (default) paces events at "
    "min_pacing_ms wall clock between events.",
)
@click.option(
    "--burst",
    is_flag=True,
    default=False,
    help="Override pacing: fire events as fast as possible (no sleeps). "
    "May race the listener subscription and dwell minimums; useful only "
    "for stress / smoke tests.",
)
@click.option(
    "--min-pacing-ms",
    type=int,
    default=None,
    help="Minimum wall-clock ms between events. "
    "Default: 100 (fast), 0 (burst), 0 (real-time floor).",
)
def trace_replay(
    fixture_path: str,
    nats_url: str,
    real_time: bool,
    burst: bool,
    min_pacing_ms: int | None,
) -> None:
    """Replay a JSON trace fixture through the senses → state pipeline."""
    from .services.senses.service import SensesService
    from .services.senses.sources.trace import TraceRunner
    from .services.state.service import StateService

    # Resolve pacing:
    #   --burst                       → 0 (override; user opted out of pacing)
    #   --real-time                   → 0 (honor recorded offsets exactly)
    #   default (--fast, no --burst)  → 100 ms wall between events
    if min_pacing_ms is None:
        if burst:
            min_pacing_ms = 0
        elif real_time:
            min_pacing_ms = 0
        else:
            min_pacing_ms = 100

    repo_root = Path(__file__).resolve().parent.parent.parent
    nats_conf = repo_root / "ops" / "natsconfig" / "nats.conf"
    nats_proc = subprocess.Popen(
        ["nats-server", "-c", str(nats_conf)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    async def run() -> None:
        # Subscriber that prints state.changed.
        from .messages import StateChanged

        async with AegisBus.connect(nats_url) as listener:
            async def print_state(msg: StateChanged) -> None:
                click.echo(
                    f"[state] {msg.previous} → {msg.current}  ({msg.reason})"
                )

            await listener.subscribe("state.changed", StateChanged, print_state)
            await listener.flush()

            state_service = StateService(
                nats_url=nats_url,
                tick_ms=100,
                accelerate_for_test=1.0 if real_time else 50.0,
            )
            senses_service = SensesService(
                nats_url=nats_url,
                sources=[
                    TraceRunner(
                        fixture_path,
                        real_time=real_time,
                        min_pacing_ms=min_pacing_ms,
                    )
                ],
            )

            # Start state first so subscriptions are live before senses publishes.
            state_task = asyncio.create_task(state_service.run())
            await asyncio.sleep(0.3)
            senses_task = asyncio.create_task(senses_service.run())
            tasks = [state_task, senses_task]
            # When the senses task completes (fixture exhausted), give state a
            # short window to flush, then shut down.
            await asyncio.wait(
                [senses_task], return_when=asyncio.FIRST_COMPLETED, timeout=30
            )
            await asyncio.sleep(0.5)
            state_service.shutdown()
            senses_service.shutdown()
            await asyncio.gather(*tasks, return_exceptions=True)

    try:
        asyncio.run(run())
    finally:
        nats_proc.terminate()
        try:
            nats_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            nats_proc.kill()


@main.group()
def memory() -> None:
    """Inspect the memory store — field notes of a quiet organism."""


@memory.command("inspect")
@click.option("--db", default="/tmp/aegis-memory.db", help="SQLite path.")
@click.option(
    "--raw",
    is_flag=True,
    default=False,
    help="Include the raw event tail at the bottom (secondary).",
)
@click.option(
    "--limit",
    default=20,
    help="Raw-event tail length (only used with --raw).",
)
def memory_inspect(db: str, raw: bool, limit: int) -> None:
    """Show consolidated Moments and themes from the memory store.

    Tone is anthropological / archival (spec §10): Moments and themes lead;
    raw event telemetry is secondary and only shown with --raw.
    """
    from datetime import datetime as _dt

    from .storage._conn import connect as _connect
    from .storage.events import EventStore as _EventStore
    from .storage.moments import MomentStore as _MomentStore
    from .storage.schema import run_migrations as _run_migrations
    from .storage.themes import ThemeStore as _ThemeStore

    def _hhmm(iso: str | None) -> str:
        if not iso:
            return "—"
        try:
            return _dt.fromisoformat(iso).strftime("%H:%M")
        except Exception:
            return iso[:16]

    conn = _connect(db)
    _run_migrations(conn)

    consolidated = _MomentStore(conn).query(state="consolidated", limit=50)
    tentative = _MomentStore(conn).query(state="tentative", limit=50)
    fading = _MomentStore(conn).query(state="fading", limit=50)
    themes = _ThemeStore(conn).query(limit=50)

    click.echo("── Moments ────────────────────────────────────")
    if not consolidated:
        click.echo("  (none yet)")
    for m in consolidated:
        start = _hhmm(m["started_at_utc"])
        end = _hhmm(m["ended_at_utc"])
        summary = m["summary"] or "(no summary)"
        click.echo(f"  {start}–{end}  {summary}")
        click.echo(f"    state: consolidated")
    click.echo("")

    click.echo(
        f"── Tentative: {len(tentative)}   Fading: {len(fading)} ──"
    )
    click.echo("")

    click.echo("── Themes ─────────────────────────────────────")
    if not themes:
        click.echo("  (none yet)")
    for t in themes:
        click.echo(
            f"  {t['key']:<24s}  · seen {t['reinforcement_count']}x"
        )
    click.echo("")

    if raw:
        events = _EventStore(conn).recent(limit=limit)
        click.echo("── Raw event tail (secondary) ─────────────────")
        for e in events:
            click.echo(f"  {e['timestamp_utc']}  {e['subject']}")

    conn.close()


@main.group()
def interventions() -> None:
    """Inspect the intervention log — what the Steward almost-said."""


@interventions.command("inspect")
@click.option("--db", default="/tmp/aegis-memory.db", help="SQLite path.")
@click.option("--limit", default=50, help="Items per section.")
def interventions_inspect(db: str, limit: int) -> None:
    """Show aired and vetoed interventions from the log."""
    from datetime import datetime as _dt

    from .storage._conn import connect as _connect
    from .storage.interventions import InterventionStore as _IS
    from .storage.scar_tissue import ScarTissueStore as _ST
    from .storage.schema import run_migrations as _rm

    def _hhmm(iso: str | None) -> str:
        if not iso:
            return "—"
        try:
            return _dt.fromisoformat(iso).strftime("%H:%M")
        except Exception:
            return iso[:16]

    conn = _connect(db)
    _rm(conn)
    store = _IS(conn)
    aired = store.query_aired(limit=limit)
    vetoed = store.query_vetoed(limit=limit)
    scar = _ST(conn).all_classes()

    click.echo("── Aired ──────────────────────────────────────")
    if not aired:
        click.echo("  (silence)")
    for row in aired:
        ack = (
            "ack" if row["acknowledged"] == 1
            else "unack" if row["acknowledged"] == 0
            else "—"
        )
        click.echo(
            f"  {_hhmm(row['timestamp_utc'])}  {row['text']}"
        )
        click.echo(
            f"    class={row['intervention_class']}  "
            f"weight={row['weight']:.1f}  conf={row['confidence']:.2f}  {ack}"
        )
    click.echo("")

    click.echo("── Vetoed ─────────────────────────────────────")
    if not vetoed:
        click.echo("  (nothing tried)")
    for row in vetoed:
        import json as _json

        reasons = _json.loads(row["reasons_json"] or "[]")
        click.echo(
            f"  {_hhmm(row['timestamp_utc'])}  {row['text']}"
        )
        click.echo(
            f"    class={row['intervention_class']}  "
            f"reasons={', '.join(reasons)}"
        )
    click.echo("")

    click.echo("── Scar tissue (per class) ────────────────────")
    if not scar:
        click.echo("  (none)")
    for k, v in scar.items():
        click.echo(f"  {k:<24s}  penalty={v:.3f}")

    conn.close()


@main.group()
def voice() -> None:
    """Voice service inspection."""


@voice.command("tail")
@click.option("--log", default="/tmp/aegis-voice.log", help="Voice log path.")
def voice_tail(log: str) -> None:
    """Tail the voice service log file."""
    import time as _time
    from pathlib import Path as _Path

    p = _Path(log)
    if not p.exists():
        click.echo(f"(no log yet at {log})")
        # Wait for it.
        while not p.exists():
            _time.sleep(0.5)
    with open(p, "r", encoding="utf-8") as f:
        f.seek(0, 2)  # end
        try:
            while True:
                line = f.readline()
                if line:
                    click.echo(line.rstrip("\n"))
                else:
                    _time.sleep(0.25)
        except KeyboardInterrupt:
            pass


@main.group()
def mood() -> None:
    """Mood service inspection."""


@mood.command("watch")
@click.option("--nats-url", default="nats://127.0.0.1:4222")
def mood_watch(nats_url: str) -> None:
    """Subscribe to mood.changed and print events as they arrive."""
    from .messages import MoodChanged

    async def run() -> None:
        async with AegisBus.connect(nats_url) as bus:
            async def on_mood(msg: MoodChanged) -> None:
                click.echo(
                    f"[{msg.timestamp.strftime('%H:%M:%S')}] "
                    f"{msg.palette.value:<22s}  "
                    f"breath={msg.breath_cadence_seconds:.1f}s  "
                    f"warmth={msg.warmth:.2f}  ({msg.reason})"
                )

            await bus.subscribe("mood.changed", MoodChanged, on_mood)
            await bus.flush()
            click.echo("(watching mood.changed; Ctrl-C to stop)")
            try:
                while True:
                    await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                pass

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


@main.command()
@click.option("--nats-url", default="nats://127.0.0.1:4222")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8080, type=int)
@click.option("--db", default="/tmp/aegis-memory.db")
@click.option("--schedule", default=None, help="Path to schedule.yaml (defaults to repo).")
def observer(nats_url: str, host: str, port: int, db: str, schedule: str | None) -> None:
    """Start the observer cockpit on http://host:port/."""
    from .services.observer.service import ObserverService

    async def run() -> None:
        import signal as _signal
        repo_root = Path(__file__).resolve().parent.parent.parent
        nats_conf = repo_root / "ops" / "natsconfig" / "nats.conf"
        nats_proc = subprocess.Popen(
            ["nats-server", "-c", str(nats_conf)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        service = ObserverService(
            nats_url=nats_url,
            host=host,
            port=port,
            db_path=db,
            schedule_path=schedule,
        )
        task = asyncio.create_task(service.run())
        click.echo(f"Observer cockpit: http://{host}:{port}/")
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (_signal.SIGINT, _signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        try:
            await stop.wait()
        finally:
            service.shutdown()
            await asyncio.gather(task, return_exceptions=True)
            nats_proc.terminate()
            try:
                nats_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                nats_proc.kill()

    asyncio.run(run())


if __name__ == "__main__":
    main()
