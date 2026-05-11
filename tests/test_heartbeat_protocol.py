"""Verify the heartbeat service emits correct UART frames.

Uses a pty pair so no real RP2040 is needed for this test.
"""
import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware" / "heartbeat"))
from uart_link import OPCODE_SET_STATE, decode_frame  # noqa: E402

from aegis_core.bus import AegisBus
from aegis_core.messages import PresenceState, StateChanged
from aegis_core.services.heartbeat.service import HeartbeatService


@pytest.mark.asyncio
@pytest.mark.timeout(15)
async def test_heartbeat_emits_set_state_frame(nats_server):
    primary, replica = os.openpty()
    replica_path = os.ttyname(replica)

    service = HeartbeatService(nats_url=nats_server, uart_path=replica_path)
    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.4)  # let it subscribe + open UART

    async with AegisBus.connect(nats_server) as bus:
        await bus.publish(
            "state.changed",
            StateChanged(
                timestamp=datetime.now(UTC),
                previous=PresenceState.DORMANT,
                current=PresenceState.ATTENTIVE,
                reason="test",
            ),
        )
        await bus.flush()
        await asyncio.sleep(0.4)

    # Read what the service wrote into the pty.
    os.set_blocking(primary, False)
    chunks: list[bytes] = []
    try:
        while True:
            data = os.read(primary, 1024)
            if not data:
                break
            chunks.append(data)
    except BlockingIOError:
        pass

    service.shutdown()
    await asyncio.wait_for(task, timeout=5)
    os.close(primary)
    os.close(replica)

    blob = b"".join(chunks)
    # Find a SET_STATE frame for ATTENTIVE (ordinal=3).
    i = 0
    found = False
    while i < len(blob) - 4:
        if blob[i] == 0xA5:
            length = blob[i + 1]
            end = i + 2 + length + 2
            if end <= len(blob):
                try:
                    opcode, body = decode_frame(blob[i:end])
                    if opcode == OPCODE_SET_STATE and body == bytes([3]):
                        found = True
                        break
                except Exception:
                    pass
                i = end
                continue
        i += 1
    assert found, f"no SET_STATE(ATTENTIVE=3) frame found in: {blob!r}"
