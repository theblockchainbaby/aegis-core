import asyncio

import pytest


class _FakeProc:
    """Stands in for the nats-server Popen handle. Reports alive for a few
    polls, then reports exited with returncode 1."""

    def __init__(self, alive_polls: int = 2) -> None:
        self._alive_polls = alive_polls
        self.pid = 99999
        self.returncode = None

    def poll(self):
        if self._alive_polls > 0:
            self._alive_polls -= 1
            return None
        self.returncode = 1
        return 1


class _FakeService:
    """Stands in for an Aegis service. run() blocks until shutdown()."""

    def __init__(self) -> None:
        self.shutdown_called = False
        self._stop = asyncio.Event()

    async def run(self) -> None:
        await self._stop.wait()

    def shutdown(self) -> None:
        self.shutdown_called = True
        self._stop.set()


@pytest.mark.asyncio
async def test_supervise_exits_nonzero_and_tears_down_when_nats_dies():
    from aegis_core import cli

    proc = _FakeProc(alive_polls=2)
    services = [_FakeService(), _FakeService(), _FakeService()]

    exit_code = await cli._supervise(proc, services, poll_interval=0.01)

    assert exit_code == 1, "supervise must return nonzero when NATS dies"
    assert all(
        s.shutdown_called for s in services
    ), "every child service must be torn down when NATS dies"
