# Memory + Moments (Plan C)

This file explains the memory layer shipped in Plan C. Read it before
touching anything in `src/aegis_core/storage/` or
`src/aegis_core/services/{memory,keeper}/`.

## What memory does (Plan C)

The `memory` service subscribes to every `senses.*` and `state.changed`
event and writes them to a SQLite events table. While the user is
present (state is OBSERVING, ATTENTIVE, or REFLECTIVE), a **tentative
Moment** is open; every sense event accumulates into the Moment's
signature. When state transitions out, the Moment is closed. Moment
boundaries derive from `msg.timestamp` — the event time, not the
recipient's wall clock — so trace replay and acceleration produce
deterministic timelines.

The `keeper` service runs consolidation:

- **Consolidated** Moments are durable — closed sessions with real
  signal (focus_score, posture_events, voice_events) and ≥ 30s duration.
- **Fading** Moments are decaying — orphans, too-short, or no-signal.
  They survive for 7 days before delete.
- **Tentative** Moments that are short but have *some* signal stay
  tentative (Ghost Moment psychology: short ambiguous Moments get a
  chance to reinforce before fading).
- **Themes** are simple keyword tokens extracted from consolidated
  Moments' summary text. Stopword-filtered. Plan E replaces this with
  embedding-derived themes when `mind` actually retrieves them.

## What memory does NOT do (yet)

- Publish `memory.continuity_candidate` events. That's Plan D/E when
  `mind`/`steward` start consuming.
- Hold embeddings. Plan E.
- Track mood timeseries inside Moments. Plan E.
- Track `acknowledged_interventions` counts. Plan D when Steward exists.

## Files

| Path | Responsibility |
|---|---|
| `storage/_conn.py` | SQLite connection (WAL, foreign keys on) |
| `storage/schema.py` | DDL + migration runner; v1 |
| `storage/events.py` | EventStore — insert + recent |
| `storage/moments.py` | MomentStore — open / close / promote / query |
| `storage/themes.py` | ThemeStore — upsert / query / decay |
| `services/memory/signature.py` | Per-Moment accumulator (pure) |
| `services/memory/service.py` | Bus → DB; Moment open/close on state |
| `services/keeper/consolidation.py` | Classification rules (pure) |
| `services/keeper/theme_tokenizer.py` | Summary → theme keys (pure) |
| `services/keeper/service.py` | consolidate_now() + fade_out() |

## Open-state semantics

A Moment is "open" while the Presence State Machine is in any of:

- `OBSERVING`
- `ATTENTIVE`
- `REFLECTIVE`

Reflective is included so cognition that happens inside a Reflective
window stays visible to memory. The signature accumulates events for as
long as the Moment is open; close happens on the transition out.

## Tuning the consolidation thresholds

Live in `services/keeper/consolidation.py`. Defaults (Plan C):

- `MIN_DURATION_S_FOR_CONSOLIDATE = 30.0`
- `FOCUS_THRESHOLD = 0.5`
- `SUSTAINED_POSTURE_EVENTS = 5`
- `ORPHAN_TIMEOUT_H = 24.0`
- `FADE_LIFETIME_DAYS = 7.0`
- Keep-tentative rule: `duration < 300s AND posture_events >= 1 → keep`

These are starting points. The 90-day dogfood phase is for adjusting them
based on what feels right when you read `aegis-core memory inspect`.

## Observer rule

Per spec §10.2: the memory inspector (CLI in Plan C, web UI in Plan F)
must never become analytics. No streaks. No engagement scores. No
optimization dashboards. Moments and themes lead; raw event telemetry is
secondary and only shown with `--raw`. It reads like field notes of a
quiet organism.
