"""Base class for all Aegis Core services.

A service is a long-running async loop that:
- connects to the NATS bus
- subscribes to its inputs
- shuts down cleanly on signal
"""
from __future__ import annotations

import asyncio
import signal
from typing import Any

import structlog

from ..bus import AegisBus

log = structlog.get_logger()


class AegisService:
    name: str = "aegis-service"

    def __init__(self, nats_url: str = "nats://127.0.0.1:4222") -> None:
        self._nats_url = nats_url
        self._shutdown = asyncio.Event()

    async def setup(self, bus: AegisBus) -> None:
        """Override to subscribe + initialize. Called once at startup."""

    async def main(self, bus: AegisBus) -> None:
        """Override for the main loop. Default just waits for shutdown."""
        await self._shutdown.wait()

    async def teardown(self, bus: AegisBus) -> None:
        """Override to clean up. Called once at shutdown."""

    async def run(self) -> None:
        log.info("service.starting", service=self.name)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.shutdown)
            except NotImplementedError:
                # Windows or some test envs — fall through.
                pass

        async with AegisBus.connect(self._nats_url) as bus:
            await self.setup(bus)
            try:
                await self.main(bus)
            finally:
                await self.teardown(bus)
        log.info("service.stopped", service=self.name)

    def shutdown(self, *_: Any) -> None:
        self._shutdown.set()
