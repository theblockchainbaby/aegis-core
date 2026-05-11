# Heartbeat UART Protocol

115200 baud, 8N1. Jetson is the host; MCU is the responder.

## Frame

```
+------+--------+-----------------+-----------+
| 0xA5 | length | opcode + body   | CRC-16 BE |
+------+--------+-----------------+-----------+
   1B      1B          1..254B          2B
```

- `length` = number of payload bytes (opcode + body), 1..254.
- CRC-16/CCITT-FALSE over `length + payload`.

## Opcodes

| Code | Name | Dir | Body |
|------|------|-----|------|
| 0x01 | SET_STATE | host→mcu | 1 byte: state ordinal (Sleep=0..Quiet=6) |
| 0x02 | SET_CADENCE | host→mcu | 2 bytes BE: cadence × 100 (centiseconds) |
| 0x03 | SET_MIC_DISABLED | host→mcu | 1 byte: 0 / 1 |
| 0x10 | HEARTBEAT | host→mcu | empty (keep-alive) |
| 0x80 | ACK | mcu→host | 1 byte: echoed opcode |
| 0x81 | NACK | mcu→host | 1 byte: echoed opcode |
| 0x82 | REVERIE_ENTER | mcu→host | empty |
| 0x83 | REVERIE_EXIT | mcu→host | empty |

## State ordinals

```
0 sleep      4 settling
1 dormant    5 reflective
2 observing  6 quiet
3 attentive
```

## Brain Reverie

The MCU starts a 5-second timer on every received frame. If the timer
expires:
- Emit REVERIE_ENTER.
- Slow the breath cadence by +1.5 s.
- Dim the palette by 30 %.

On any subsequent valid frame, emit REVERIE_EXIT and restore the prior
cadence + palette.
