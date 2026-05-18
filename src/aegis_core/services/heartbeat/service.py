"""Heartbeat service — Jetson side of the UART link to the RP2040.

Subscribes to `state.changed` and pushes SET_STATE frames to the MCU.
Sends a HEARTBEAT frame every 2 s as keep-alive so the MCU never enters
Brain Reverie just because the bus is quiet.

On startup, opens the UART. On shutdown, releases it.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import structlog

# Plan A: use the firmware/heartbeat directory directly so we share the
# framing module. Plan F will lift this into src/.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "firmware" / "heartbeat"))

from privacy_state import STATE_ORDINALS
from uart_link import (
    OPCODE_HEARTBEAT,
    OPCODE_SET_STATE,
    encode_frame,
)

from ...bus import AegisBus
from ...messages import StateChanged
from .._base import AegisService

log = structlog.get_logger()

HEARTBEAT_INTERVAL_S = 2.0


class HeartbeatService(AegisService):
    name = "heartbeat"

    def __init__(self, uart_path: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._uart_path = uart_path or os.environ.get(
            "AEGIS_HEARTBEAT_UART",
            "/dev/tty.usbmodem-default",
        )
        self._uart = None

    def _open_uart(self):
        import serial  # local import so pure-host tests don't need pyserial

        self._uart = serial.Serial(self._uart_path, baudrate=115200, timeout=0.1)

    async def setup(self, bus: AegisBus) -> None:
        try:
            self._open_uart()
        except Exception as e:
            log.warning("heartbeat.uart_open_failed", error=str(e))
            self._uart = None

        async def on_state(msg: StateChanged) -> None:
            ordinal = STATE_ORDINALS.get(msg.current.value, 1)
            frame = encode_frame(OPCODE_SET_STATE, bytes([ordinal]))
            if self._uart:
                self._uart.write(frame)

        await bus.subscribe("state.changed", StateChanged, on_state)

    async def main(self, bus: AegisBus) -> None:
        async def keepalive() -> None:
            while not self._shutdown.is_set():
                if self._uart:
                    try:
                        self._uart.write(encode_frame(OPCODE_HEARTBEAT, b""))
                    except Exception as e:
                        log.warning("heartbeat.write_failed", error=str(e))
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)

        task = asyncio.create_task(keepalive())
        try:
            await self._shutdown.wait()
        finally:
            task.cancel()
            with contextlib_suppress():
                await task

    async def teardown(self, bus: AegisBus) -> None:
        if self._uart:
            try:
                self._uart.close()
            except Exception:
                pass


def contextlib_suppress():
    import contextlib

    return contextlib.suppress(asyncio.CancelledError, Exception)


def make_service(**kwargs) -> HeartbeatService:
    return HeartbeatService(**kwargs)
