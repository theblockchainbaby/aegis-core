"""Reusable skeleton that answers ping/pong on its own subject.

Used by Plan A to wire all nine services into the bus without giving any of
them real behavior yet. Plans B–F replace these stubs one at a time.
"""
from __future__ import annotations

from ..bus import AegisBus
from ._base import AegisService


class StubService(AegisService):
    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = name

    async def setup(self, bus: AegisBus) -> None:
        async def on_ping(raw):
            target = raw.data.decode()
            if target == self.name:
                await bus._nc.publish(
                    f"ping.reply.{self.name}",
                    f"pong from {self.name}".encode(),
                )

        await bus._nc.subscribe("ping.request", cb=on_ping)
