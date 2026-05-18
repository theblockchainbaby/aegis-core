"""Shared pytest fixtures."""
import asyncio
import socket
import subprocess
import time
from pathlib import Path

import pytest


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def nats_server(tmp_path: Path):
    """Spawn a local nats-server bound to a temp port and Unix socket.

    Yields the TCP URL. Server is killed at teardown.
    """
    port = _find_free_port()
    sock = tmp_path / "nats.sock"
    config = tmp_path / "nats.conf"
    config.write_text(
        f'listen: "127.0.0.1:{port}"\n'
        f'jetstream {{ store_dir: "{tmp_path}/js" }}\n'
    )
    proc = subprocess.Popen(
        ["nats-server", "-c", str(config)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for the port to come up.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.socket() as s:
                s.connect(("127.0.0.1", port))
            break
        except OSError:
            await asyncio.sleep(0.05)
    else:
        proc.kill()
        raise RuntimeError("nats-server failed to start")

    try:
        yield f"nats://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
