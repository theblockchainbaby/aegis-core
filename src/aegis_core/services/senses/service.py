"""senses service — orchestrates pluggable Sources, publishes to the bus.

Each Source is its own async iterator. We pump them in parallel and forward
every (subject, message) pair to the typed AegisBus.
"""
from __future__ import annotations

import asyncio
from collections.abc import Sequence

import structlog

from ...bus import AegisBus
from .._base import AegisService
from .sources.protocol import Source

log = structlog.get_logger()


class SensesService(AegisService):
    name = "senses"

    def __init__(self, sources: Sequence[Source] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sources: list[Source] = list(sources or [])

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus

    async def main(self, bus: AegisBus) -> None:
        if not self._sources:
            log.warning("senses.no_sources_configured")
            await self._shutdown.wait()
            return

        async def pump(source: Source) -> None:
            try:
                async for subject, msg in source.events():
                    if self._shutdown.is_set():
                        break
                    await bus.publish(subject, msg)
            finally:
                await source.aclose()

        tasks = [asyncio.create_task(pump(s)) for s in self._sources]
        try:
            done, pending = await asyncio.wait(
                tasks + [asyncio.create_task(self._shutdown.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    async def teardown(self, bus: AegisBus) -> None:
        for s in self._sources:
            try:
                await s.aclose()
            except Exception:
                pass


def make_service(**kwargs) -> SensesService:
    return SensesService(**kwargs)
