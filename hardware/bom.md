# Aegis Core v1 — Hardware BOM

**Target unit cost:** ~$510 (single-unit prototype).
**Lead time:** budget 7–14 days for slow movers (Jetson, ReSpeaker).

## Compute

| Item | Source | Cost | Notes |
|---|---|---|---|
| Jetson Orin Nano Super dev kit | NVIDIA / Arrow / SparkFun | $249 | Includes carrier + heatsink |
| Seeed XIAO RP2040 | Seeed Studio | $5 | The heartbeat MCU |
| 256 GB NVMe SSD (M.2 2280) | Amazon | $30 | Faster than SD; needed for memory engine |
| Noctua NF-A4x10 5V PWM (40mm) | Amazon | $15 | Replaces stock Jetson fan |

## Sensors

| Item | Source | Cost | Notes |
|---|---|---|---|
| IMX219 camera module + 120° wide lens | Arducam | $25 | CSI ribbon to Jetson |
| ReSpeaker 4-Mic Linear Array | Seeed Studio | $25 | USB |
| MAX98357 I²S amplifier breakout | Adafruit | $6 | |
| 2W full-range 4Ω speaker (50mm) | Adafruit | $9 | Voice-band tuned chamber required (see hardware/shell) |
| Seeed MR24HPC1 24GHz mmWave radar | Seeed Studio | $20 | UART |
| VEML7700 ambient light sensor breakout | Adafruit | $5 | I²C |
| PCT2075 temperature sensor breakout | Adafruit | $5 | I²C — placed near Jetson exhaust |

## LED face

| Item | Source | Cost | Notes |
|---|---|---|---|
| SK6812 RGBW LED strip (60 LED/m, 1m) | Adafruit | $25 | Cut into two strips — top arc + bottom edge |
| 1mm frosted polycarbonate sheet (A5) | McMaster | $12 | Diffuser |

## Power + interconnect

| Item | Source | Cost | Notes |
|---|---|---|---|
| 12V/5A barrel-jack PSU + braided cable | Amazon | $25 | |
| USB-C front-panel jack | Adafruit | $4 | Service port |
| JST-SH cables (assorted) | Amazon | $8 | Sensor wiring |
| Small protoboard / carrier | Adafruit | $10 | Plan F will replace with real PCB |

## Shell (3D-printed v1)

| Item | Source | Cost | Notes |
|---|---|---|---|
| PETG filament (1kg, black) | Amazon | $20 | Inner structural cage |
| Matte gray MJF outer skin (1 print) | Shapeways / JLC3DP | $35 | Outer aesthetic |
| Silicone non-slip pad | Amazon | $5 | Base |
| 4× magnetic alignment posts (5mm N52) | Amazon | $7 | Shell-swap interface |

## Misc

| Item | Source | Cost | Notes |
|---|---|---|---|
| Smoked acrylic strip (50×100mm, 1mm) | TAP Plastics | $10 | Camera + mic-array window |
| Heatsink thermal pads | Amazon | $5 | |
| Assorted M2/M3 hardware | Amazon | $10 | Mounting |

**Subtotal:** ~$510

## Procurement order

1. Place orders for slow-movers FIRST (Jetson, ReSpeaker, MJF skin print).
2. Place fast-mover batch second (Adafruit run: MAX98357, IMX219, VEML7700, PCT2075, USB-C, SK6812, MR24HPC1, NeoPixel diffuser).
3. Pick up filament + acrylic locally if possible.

## Verification on arrival

For each item, before integration:
- [ ] Visual inspection — no damage, correct revision.
- [ ] Power-on smoke test where applicable (Jetson, RP2040, sensors that have a self-test mode).
- [ ] Log the part's serial / lot in `hardware/inventory.md` (created on first item arrival).
