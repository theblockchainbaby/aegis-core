# Observer Cockpit (Plan F)

Read this before touching `src/aegis_core/services/observer/`.

## What this plan added

A localhost-only web cockpit + scheduler + snapshots + dogfood mode.
The point of Plan F is **legibility, not intelligence.** The observer
reads what already exists and makes it visible. It does NOT generate new
cognition, mood, or memory.

## The cockpit

`aegis-core observer start` launches uvicorn on `127.0.0.1:8080`. The
service:

- Subscribes to all major bus subjects and maintains a 500-event ring
  buffer in memory.
- Serves a server-rendered HTML index at `/`.
- Streams live events via SSE at `/sse/events`.
- Exposes JSON endpoints: `/api/now`, `/api/timeline`,
  `/api/snapshots/{date}`, `/api/dogfood`.

The HTML is deliberately plain (spec §10.2: anthropological, never
analytical). No charts, no streaks, no engagement scores.

## Snapshots

`/api/snapshots/{date}` returns a daily summary derived from
`interventions`, `moments`, and `events`. The observer writes the same
JSON to `data/snapshots/YYYY-MM-DD.json` for offline export. Daily only —
no weekly aggregation, no list endpoint. Reach for weekly only when the
dogfood phase actually reveals the need.

## Scheduler (TEMPORARY)

`rules/schedule.yaml` configures four daily triggers:

- `morning_reflection` → publishes `state.changed → REFLECTIVE`
- `evening_reflection` → publishes `state.changed → REFLECTIVE`
- `quiet_hours_start` → publishes `state.changed → SLEEP`
- `quiet_hours_end` → publishes `state.changed → DORMANT`

The scheduler ticks every 30 seconds and fires once per day per trigger.
This is **observable** like everything else: the synthetic state event
flows through the bus, gets logged, shows up in the timeline. Every
cause is traceable.

The scheduler module's docstring marks itself TEMPORARY — Plan F' will
replace the `previous=DORMANT` placeholder with a real read of the
buffer's most recent state, and may swap in richer triggers. Resist
generalizing it further now.

## Dogfood mode

`aegis-core dogfood start` writes `dogfood_started_at` to the SQLite
`meta` table. `/api/dogfood` returns day N of 90 + the live aired/vetoed
totals. The cockpit shows the day count next to the rest of the
inventory.

## What Plan F does NOT do

- No new cognition (mind unchanged from Plan E).
- No new memory or mood logic.
- No analytics layer (forbidden by spec §10.2).
- No hot reload of `rules/intervention.yaml` — deferred.
- No multi-user / authentication / network exposure.
- No hardware UI / mobile app.

## Capstone

`tests/test_canonical_cycle_observer.py` brings up the full chain
(memory + keeper + mind + steward + voice + mood + observer), drives
one REFLECTIVE state, and asserts the cockpit's `/api/now` reflects:

- Current state == REFLECTIVE.
- Last utterance present with the expected content.
- Mood palette == REFLECTIVE_VIOLET.
- Restraint counts incremented.

That's legibility working end-to-end.
