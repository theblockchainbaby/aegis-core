# The Steward (Plan D)

Read this before changing anything in `src/aegis_core/services/steward/`
or the intervention/scar_tissue storage layer.

## What the Steward is

The Steward is the gatekeeper between cognition and speech. It receives
`mind.utterance_proposal` events; for each one it runs a deterministic
gate; the gate either lets the utterance through (publishing
`voice.speak` and logging `aired`) or vetoes it (logging the decision
with structured reasons). Most proposals are vetoed.

Per spec principle 20: **the Steward IS the product.** Not the LLM, not
the memory system, not the sensors. Computational social restraint is
the category-defining innovation. Treat the gate as the highest-discipline
code in the repo.

The Plan D capstone proves this empirically: over a noisy 20-proposal
stream, the Steward let 1 through and vetoed 19. That 19:1 ratio is the
behavioral signature of restraint.

## The gate (pure arithmetic)

`services/steward/gate.py::evaluate` is a pure function:

```
evaluate(proposal, gate_state, rules, tone, signals, clock) → Decision
```

A proposal passes only if EVERY check passes. Veto reasons accumulate
in a contractually-ordered list:

1. `wrong_state` — presence state is not in `allowed_states_for_speech` (Plan D: REFLECTIVE only).
2. `confidence_below_threshold` — confidence < baseline + scar_tissue_penalty + recovery_bump.
3. `silence_budget_exhausted` — budget remaining < proposal.weight × presence_decay_multiplier.
4. `daily_cap_reached` — utterances today ≥ daily cap.
5. `hourly_cap_reached` — time since last utterance < (1 hour / hard_cap_per_hour).
6. `forbidden_tone:*` — one entry per detected tone, in classifier order.
7. `competing_for_attention` — typing, calls, video, or recent activity detected.

The order is **contractual**. Downstream consumers read `reasons[0]` as
the *primary* veto cause. Reshuffling silently would corrupt future
learned attribution. See `gate.py` module docstring for the full contract.

## The five mechanisms

| Mechanism | Lives in | Persists? | Time scale |
|---|---|---|---|
| Silence Budget | `service.py` (in-memory token bucket) | No (resets on restart) | Per-day refill |
| Intervention Weights | `rules.py` (loaded from YAML) | Static | N/A |
| Scar Tissue | `storage/scar_tissue.py` | Yes (SQLite) | Long-arc per class |
| Social Recovery | `recovery.py` | No (in-memory) | Short-arc (minutes) |
| Presence Decay | `decay.py` | No (in-memory, restarts cold) | Long-arc (weeks) |

Scar tissue is the only one that survives a restart in Plan D. Silence
budget, social recovery, and presence decay all reset on boot — acceptable
for dogfood-on-self; Plan F's observer can persist budget state if needed.

## The rules file

Lives at `rules/intervention.yaml`. Pydantic-validated on load. Plan D
loads at service startup; restart Steward to apply changes. Hot reload
is a Plan F (observer cockpit) deliverable.

Tunable values (every Plan D number is a starting point, not a law):

- `silence_budget.default_weight_per_day` — 3.0 starting budget
- `silence_budget.hard_cap_per_hour` — 1 (max one utterance per hour)
- `silence_budget.hard_cap_per_day` — 5
- `confidence_threshold.default` — 0.85
- `confidence_threshold.social_recovery_window` — 0.93
- `intervention_weights.*` — 0.1 / 0.5 / 1.0 / 2.0
- `social_recovery.trigger.utterance_unacknowledged_for_seconds` — 60
- `presence_decay.measurement_window_days` — 7
- `conversational_scar_tissue.cap` — 0.15

## The intervention log

Every decision lands in `interventions` (SQLite, schema v2). The log is
the source of truth for `aegis-core interventions inspect` and (Plan F)
the observer cockpit.

The decision column is a three-value enum (CHECK-enforced):

- `aired` — proposal cleared the gate; `voice.speak` was published.
- `vetoed` — proposal failed the gate; `reasons_json` carries the
  ordered list of failure causes.
- `soft_vetoed` — RESERVED for Plan E. Distinct from `vetoed`: "not now,
  ask again later" (postponed utterances, wait-for-better-pause). Plan
  D never emits this value; the schema reserves it so the future
  mechanism doesn't require a migration.

Per spec §10: **the log is anthropological, never analytical.** No
streaks, no ratios framed as KPIs, no engagement scores. The CLI shows
aired and vetoed entries side by side with reasons. That's the right
relationship to the data.

## The capstone test

`tests/test_canonical_cycle_steward.py` proves more vetoes than aired
utterances over a noisy proposal stream. The asserted ratio (vetoed ≥
2 × aired) is the behavioral signature of restraint. Plan D's actual
run was 19:1.

If the ratio inverts in production over a real day, something has gone
wrong with the gate. The capstone is the canary.

## What's deferred to Plan E

- Real `mind` service (Claude API + local Gemma 2B router).
- Real `voice` service (Piper TTS + Acoustic Presence EQ).
- Real attention signals (keystroke + audio + active-window detection).
- Learned tone classifier (replacing the regex-based one).
- Mood-driven LED/breath responses to social recovery + presence decay.
- `soft_vetoed` decision class — postponed utterances ("not now").

## What's deferred to Plan F

- Hot reload of `rules/intervention.yaml` on file save.
- Web observer cockpit for the intervention log.
- Snapshot + rollback for the SQLite store.

## The discipline

If you find yourself writing code that would let the Node speak more
often, stop. Every feature in this directory is gravitationally pulled
toward "say more"; resist. The whole point is intentional scarcity.
