"""UART framing for the heartbeat link.

Pure Python (works on CPython and MicroPython). See docs/uart_protocol.md.
"""

START_BYTE = 0xA5

# Opcodes — host → MCU
OPCODE_SET_STATE = 0x01
OPCODE_SET_CADENCE = 0x02
OPCODE_SET_MIC_DISABLED = 0x03
OPCODE_HEARTBEAT = 0x10

# Opcodes — MCU → host
OPCODE_ACK = 0x80
OPCODE_NACK = 0x81
OPCODE_REVERIE_ENTER = 0x82
OPCODE_REVERIE_EXIT = 0x83


class FrameError(Exception):
    pass


def _crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE."""
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(opcode: int, body: bytes) -> bytes:
    if not (0 <= opcode <= 0xFF):
        raise ValueError("opcode out of range")
    if len(body) > 0xFE:  # length byte holds payload+opcode size
        raise ValueError("body too long")
    payload = bytes([opcode]) + body
    length = len(payload)
    crc = _crc16(bytes([length]) + payload)
    return bytes([START_BYTE, length]) + payload + bytes([(crc >> 8) & 0xFF, crc & 0xFF])


def decode_frame(frame: bytes) -> tuple[int, bytes]:
    if len(frame) < 5:
        raise FrameError("frame truncated (too short)")
    if frame[0] != START_BYTE:
        raise FrameError(f"bad start byte: 0x{frame[0]:02x}")
    length = frame[1]
    if len(frame) != 2 + length + 2:
        raise FrameError(
            f"frame length mismatch: expected {2 + length + 2}, got {len(frame)}"
        )
    payload = frame[2 : 2 + length]
    crc_recv = (frame[-2] << 8) | frame[-1]
    crc_calc = _crc16(bytes([length]) + payload)
    if crc_recv != crc_calc:
        raise FrameError(f"bad crc: got 0x{crc_recv:04x}, expected 0x{crc_calc:04x}")
    return payload[0], payload[1:]
