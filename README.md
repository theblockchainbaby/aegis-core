# aegis-core

The Desk Companion. An attempt at *ambient cognitive presence* — not an assistant.

**Status:** v1 in active build. Spec is in the partner repo at
`/Users/york/claude-ear/docs/superpowers/specs/2026-05-10-aegis-core-v1-design.md`.

**Build plan:** see `/Users/york/claude-ear/docs/superpowers/plans/`.

## Design discipline

Read `docs/principles.md` before changing any service. The Steward (the gatekeeper
that suppresses ~95% of utterance proposals) is the product, not the LLM. Every
PR is checked against the principles list.

## Local dev

```bash
uv sync
uv run aegis-core up      # starts the local NATS server + all service stubs
uv run aegis-core ping    # sanity-check the bus
uv run pytest             # runs the host-side test suite
```

## Firmware

```bash
cd firmware/heartbeat
mpremote connect /dev/tty.usbmodem* cp main.py led_face.py uart_link.py \
    privacy_state.py brain_reverie.py :
mpremote connect /dev/tty.usbmodem* reset
```

## Hardware

See `hardware/bom.md` for the v1 BOM (~$510). Shell CAD lives in `hardware/shell/`.
