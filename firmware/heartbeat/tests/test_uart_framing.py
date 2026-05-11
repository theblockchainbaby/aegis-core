"""Host-side tests for the UART framing protocol.

The same module runs on the MCU under MicroPython; tests run under CPython.
"""
import sys
from pathlib import Path

# Allow `import uart_link` from the firmware dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uart_link import (
    OPCODE_HEARTBEAT,
    OPCODE_SET_CADENCE,
    OPCODE_SET_MIC_DISABLED,
    OPCODE_SET_STATE,
    FrameError,
    decode_frame,
    encode_frame,
)


def test_encode_set_state_roundtrip():
    frame = encode_frame(OPCODE_SET_STATE, bytes([3]))
    opcode, body = decode_frame(frame)
    assert opcode == OPCODE_SET_STATE
    assert body == bytes([3])


def test_encode_set_cadence_roundtrip():
    body = (550).to_bytes(2, "big")  # 5.50 s
    frame = encode_frame(OPCODE_SET_CADENCE, body)
    opcode, decoded = decode_frame(frame)
    assert opcode == OPCODE_SET_CADENCE
    assert int.from_bytes(decoded, "big") == 550


def test_encode_heartbeat_no_body():
    frame = encode_frame(OPCODE_HEARTBEAT, b"")
    opcode, body = decode_frame(frame)
    assert opcode == OPCODE_HEARTBEAT
    assert body == b""


def test_decode_rejects_bad_start_byte():
    try:
        decode_frame(b"\x00\x01\x01\x00\x00")
    except FrameError as e:
        assert "start" in str(e).lower()
    else:
        raise AssertionError("expected FrameError")


def test_decode_rejects_bad_crc():
    frame = bytearray(encode_frame(OPCODE_SET_MIC_DISABLED, bytes([1])))
    frame[-1] ^= 0xFF  # corrupt CRC low byte
    try:
        decode_frame(bytes(frame))
    except FrameError as e:
        assert "crc" in str(e).lower()
    else:
        raise AssertionError("expected FrameError")


def test_decode_rejects_truncated_frame():
    try:
        decode_frame(b"\xA5\x02\x01")  # length says 2 but only 1 byte present
    except FrameError as e:
        assert "trunc" in str(e).lower() or "length" in str(e).lower()
    else:
        raise AssertionError("expected FrameError")
