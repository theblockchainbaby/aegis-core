"""voice service — renders VoiceSpeak events via a pluggable backend.

Plan E uses StdoutBackend; Plan E' swaps in PiperBackend.
"""
from __future__ import annotations

import structlog

from ...bus import AegisBus
from ...messages import VoiceSpeak
from .._base import AegisService
from .backend import StdoutBackend, VoiceBackend

log = structlog.get_logger()


class VoiceService(AegisService):
    name = "voice"

    def __init__(self, backend: VoiceBackend | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._backend: VoiceBackend = backend or StdoutBackend()

    async def setup(self, bus: AegisBus) -> None:
        await bus.subscribe("voice.speak", VoiceSpeak, self._on_speak)

    async def _on_speak(self, msg: VoiceSpeak) -> None:
        await self._backend.speak(msg.text)


def make_service(**kwargs) -> VoiceService:
    return VoiceService(**kwargs)
