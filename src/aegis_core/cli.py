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


if __name__ == "__main__":
    main()
