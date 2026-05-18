# Aegis Core dogfood observations

Started 2026.05.13. Day 1 of 90.

Field notes. Not tickets, not feature requests, not engineering tasks. Append only. Raw.

Each entry: timestamp, situation, what it did, reaction, classification.

**Classes:** timing / restraint / continuity / repetition / tone / presence

**Discipline:** one observation is noise. Wait for a cluster of roughly 5 in the same class before changing anything. When a cluster forms, replay through the canonical cycle harness before touching live rules.

***

## 2026.05.13 11:53 PDT · presence

**Situation:** Cold start of `aegis-core up` immediately after `dogfood start`.
**What it did:** Boot produced roughly 9 full Python stack traces (services racing NATS startup) before stabilizing. Then went silent.
**Reaction:** Felt like the organism crashed instead of waking. Awakening should breathe, not traceback.
**Note:** Likely fix when cluster forms. A NATS readiness probe before service start, or quieter retry backoff.

## 2026.05.13 11:53 PDT · presence

**Situation:** First look at cockpit at `http://127.0.0.1:8080/` after cold start.
**What it did:** Showed "No presence state recorded yet" plus "(silence)" plus 0 aired and 0 vetoed.
**Reaction:** Organism has no perceptual inputs at all on this hardware. The `senses.no_sources_configured` warning fired at boot. Without senses there are no state changes, no proposals, no restraint activity. Cockpit will stay silent except for scheduler firings.
**Note:** If by end of week the only entries are scheduler driven, this becomes a structural finding: the system needs at least one perceptual input source before it can be dogfooded.

## 2026.05.13 11:53 PDT · presence

**Situation:** Reading `rules/schedule.yaml` against the Plan F scheduler implementation.
**What it did:** YAML comment says "All times are local 24h" but `scheduler.py` calls `datetime.now(UTC)`, so times are effectively UTC.
**Reaction:** For PDT, `morning_reflection: 09:00` UTC is 02:00 local (sleep), `evening_reflection: 18:00` UTC is 11:00 local (already passed today). The scheduler's idea of "morning" is not the operator's.
**Note:** Likely fix when cluster forms. Either localize the parse or rename keys to UTC explicitly. Minor change, rule layer only.

***

## 2026.05.14 15:05 PDT · presence

**Situation:** Day 2 of 90. Asked the first look question after 21 hours of ambient run. Cockpit was running, scheduler had fired 4 times on time (Wed 22:00, Thu 07:00, 18:00, 22:00 UTC), state cleanly transitioned through sleep, dormant, reflective, sleep.
**What it did:** Operated invisibly for a full day. No notifications, no sounds, no visual pull.
**Reaction:** "I didn't notice anything."
**Note:** Ambiguous signal. Could be presence working as designed (principle 10: comfortable to ignore; principle 19: never compete for attention) OR functionally absent (no senses, no voice, only silent state transitions in a browser tab, so there is literally nothing to notice). The diagnostic question for tomorrow: would I have noticed if `up` had crashed and the cockpit died? If yes, ambient. If no, invisible.

## 2026.05.14 evening PDT · presence

**Situation:** Tried to open the cockpit in Safari after finishing the host activity sensor. Safari could not connect.
**What it did:** The `up` process (pid 37169, alive since the 2026.05.13 launch) was still running, but its NATS subprocess had died and port 8080 was no longer listening. The organism half collapsed: parent process up, bus and cockpit down. Earlier the same day the cockpit was serving normally, so NATS died sometime between then and now, likely across a machine sleep.
**Reaction:** Did not notice until the cockpit failed to load. This is the empirical answer to the Day 2 diagnostic question, would I notice if it crashed. No. The organism can die and keep looking alive from the outside.
**Note:** Presence class. Touches principle 21, failure should become behavioral, not silent collapse. Likely fix when a cluster forms: a supervisor or health check that either restarts NATS or makes `up` exit loudly when NATS dies, instead of lingering as a half dead parent. For now the fix is a manual restart of `up`.

<!-- Append new entries above this line. Keep format consistent. -->
