# Cognition, Voice, Mood (Plan E)

Read this before touching `src/aegis_core/services/{mind,voice,mood}/`.

## What this plan added

Plan E connects the organism end-to-end. The chain is:

```
memory.continuity_candidate          ┐
state.changed (REFLECTIVE)           ┼─► mind (router) ─► mind.utterance_proposal
                                     ┘                              │
                                                                    ▼
                                                                 steward (gate)
                                                                    │
                                                              aired │ vetoed
                                                                    ▼
                                                                 voice.speak ─► VoiceBackend
state.changed                        ─► mood (inference) ─► mood.changed ─► (MCU / observer)
```

Real services in Plan E:

- **`mind`** — cognition router. Local heuristic generator by default;
  Claude-stub escalation for Memory Magic Moments (when a candidate is
  available from either event or retrieval).
- **`voice`** — utterance renderer. Plan E uses StdoutBackend
  (prints + log file); Plan E' adds PiperBackend.
- **`mood`** — state-driven palette/cadence/warmth publisher.

## What's still stubbed

- **ClaudeClient → StubClaudeClient.** Returns canned, tone-safe text
  derived from input. Plan E' swaps in `AnthropicClient` (one task).
- **VoiceBackend → StdoutBackend.** Plan E' adds `PiperBackend`.
- **MoodSignals → state only.** Plan E' will weave in focus score,
  social recovery, scar tissue penalty, presence decay multiplier.

## How memory drives mind (two paths)

Plan E wires BOTH possible sources of a Memory Magic candidate:

**Path 1 — event-driven (consolidation-time):**
`KeeperService.consolidate_now_async()` publishes a
`memory.continuity_candidate` event when promoting a Moment to
`consolidated`. The `mind` service caches the most recent event (60-second
TTL — `CANDIDATE_TTL_SECONDS`). This catches Moments the instant the
keeper recognizes them.

**Path 2 — pull-driven (runtime retrieval):**
On `state.changed → REFLECTIVE`, if no fresh cached event exists, mind
queries the SQLite store for consolidated Moments within
`RETRIEVAL_WINDOW_DAYS` (default 7) and constructs a
`ContinuityCandidate` on the fly from the most recent one.

Path 2 is **non-negotiable**: keeper is a nightly/maintenance job, but
reflective cognition is runtime. Memory Magic Moments that consolidated
yesterday or last week should still be able to surface on today's
Reflective entry. Without the retrieval path, the Node would only
mention past sessions on the night they were consolidated — exactly the
wrong relationship to continuity.

When both paths could fire (a fresh event AND queryable Moments), the
event wins — it's more specific to the current cycle. The retrieval
path is the fallback.

Either way, mind passes the candidate through the redaction layer and
escalates to Claude (Stub in Plan E) for the Memory Magic phrasing.
The local heuristic generator handles ambient_note proposals only.

## Files

| Path | Responsibility |
|---|---|
| `services/mind/claude_client.py` | ClaudeClient Protocol + StubClaudeClient |
| `services/mind/redaction.py` | redact_for_cloud (pure) |
| `services/mind/local_generator.py` | Heuristic ambient_note proposals (pure) |
| `services/mind/router.py` | Local-vs-Claude routing (pure) |
| `services/mind/service.py` | Bus wiring, state + candidate tracking, runtime retrieval |
| `services/voice/backend.py` | VoiceBackend Protocol + StdoutBackend |
| `services/voice/service.py` | Bus wiring; consumes voice.speak |
| `services/mood/inference.py` | state + signals → MoodChanged (pure) |
| `services/mood/service.py` | Bus wiring; publishes on state.changed |
| `services/keeper/service.py` | Extended with consolidate_now_async() to publish continuity events |

## Redaction

`redact_for_cloud` is conservative on purpose. It drops:

- Any `bytes` value (audio, frames).
- Any key matching `audio*`, `camera*`, `frame*`, `user_email*`,
  `user_phone*`, `pii_*`, `raw_*`.
- Recurses into nested dicts.

It does NOT redact text content — the calling code's responsibility is
to NOT put text it doesn't want in the context dict. Memory summaries
are user-volunteered by definition.

## Tone safety

The StubClaudeClient is hand-tuned to phrase output as "Yesterday you
mentioned the X." — this passes the Plan D forbidden-tone classifier.
If you change the stub, run the capstone test (`test_canonical_cycle_full.py`)
to verify the output still passes.

The local generator's `_format_duration_phrase` produces "two hours
and fourteen minutes" — non-imperative; also passes the classifier.

## What Plan E does NOT do

- No real Anthropic API call. (Plan E')
- No real Piper TTS. (Plan E')
- No real attention signals. (Plan D stub still used)
- No real Gemma 2B local model. (Plan E')
- No mood persistence (transient events).
- No conversational responses (one-shot proposals only).

## Capstone

`tests/test_canonical_cycle_full.py` proves the full chain. It seeds a
consolidated Moment, brings up all four services + keeper, drives one
REFLECTIVE state, and asserts:

- Exactly 1 `VoiceSpeak` event emitted.
- The StdoutBackend printed the utterance.
- At least 1 `MoodChanged` event emitted (the REFLECTIVE transition).

That's the audible/printable utterance and the mood shift. The bones of
the canonical cycle work.
