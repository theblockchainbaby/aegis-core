"""Typed NATS bus wrapper.

All services use this module rather than calling `nats-py` directly so that
message schemas remain enforced and observability hooks (in Plan F) have a
single attach point.
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Generic, TypeVar

import nats
import structlog
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from pydantic import ValidationError

from .messages._base import AegisMessage

log = structlog.get_logger(__name__)

T = TypeVar("T", bound=AegisMessage)
Handler = Callable[[T], Awaitable[None]]


class AegisBus(Generic[T]):
    """Thin wrapper around a single NATS connection."""

    def __init__(self, nc: NATSClient) -> None:
        self._nc = nc

    @property
    def is_connected(self) -> bool:
        """True when the underlying NATS connection is live."""
        return self._nc.is_connected

    @classmethod
    @contextlib.asynccontextmanager
    async def connect(cls, url: str = "nats://127.0.0.1:4222") -> AsyncIterator[AegisBus]:
        nc = await nats.connect(url, max_reconnect_attempts=-1)
        try:
            yield cls(nc)
        finally:
            await nc.drain()

    async def publish(self, subject: str, msg: AegisMessage) -> None:
        payload = msg.model_dump_json().encode()
        await self._nc.publish(subject, payload)
        log.debug("bus.publish", subject=subject, bytes=len(payload))

    async def subscribe(
        self,
        subject: str,
        schema: type[T],
        handler: Handler[T],
    ) -> None:
        async def wrapped(raw: Msg) -> None:
            try:
                msg = schema.model_validate_json(raw.data)
            except ValidationError as e:
                log.warning("bus.invalid_payload", subject=subject, error=str(e))
                return
            try:
                await handler(msg)
            except Exception:
                log.exception("bus.handler_failed", subject=subject)

        await self._nc.subscribe(subject, cb=wrapped)
        log.debug("bus.subscribe", subject=subject, schema=schema.__name__)

    async def flush(self) -> None:
        await self._nc.flush()
