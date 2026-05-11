## 4. Software Architecture

### 4.1 Two computers, one organism

- **Jetson:** all perception, cognition, memory, intervention gating.
- **RP2040:** LED face, wake/sleep, mic power gating from mmWave, hardware privacy state, watchdog. If UART from Jetson is silent for >5 s, MCU enters **Brain Reverie** — slower drift, dimmer LED — but the organism never appears dark. After 30 s of silence MCU triggers a soft Jetson reboot.

### 4.2 Process topology on the Jetson

All services are small Python processes supervised by `systemd`, communicating over a local **NATS** message bus on a Unix domain socket.

| Service | Purpose | Subscribes | Publishes |
|---|---|---|---|
| `senses` | Camera + mic + mmWave + ambient + thermal → perception events. Whisper-base STT, YOLOv8n presence, lightweight pose, VAD. Raw frames never leave this service. | hardware | `senses.*` |
| `state` | Presence State Machine (Sleep / Dormant / Observing / Attentive / Settling / Reflective / Quiet). Owns transitions, dwell minimums, Presence Momentum. | `senses.*` | `state.changed`; responds to `state.snapshot` request-reply for any service that needs the current state on demand |
| `memory` | SQLite + sqlite-vss. Writes events, builds embeddings (BGE-small local), retrieves Moments and themes. Five typed stores: episodic, semantic, temporal, spatial, emotional. Implements Ghost Moments lifecycle. | `senses.*`, `mind.*` | `memory.continuity_candidate` |
| `mood` | Derives Ambient Mood (focus, workload, stress proxies) from `senses` + `state` + `memory`. Drives non-verbal channel: LED palette, breath cadence. | `senses.*`, `state.changed`, `memory.themes` | `mood.changed` (→ MCU) |
| `mind` | Cognition router. Default: local Gemma 2B for routine moments. Escalates to Claude API for Memory Magic Moments, novel reasoning, low-confidence local outputs. Persona = system prompt + retrieval bundle. | `state.changed` (→ Reflective), `memory.continuity_candidate` | `mind.utterance_proposal` |
| `steward` | **The gatekeeper. No speech without Steward approval.** Enforces Silence Budget, Intervention Weights, confidence thresholds, Rules of Intervention, Social Recovery, Presence Decay, Conversational Scar Tissue, "never compete for attention." Vetoes ~95% of proposals. | `mind.utterance_proposal` | `voice.speak` (rare) |
| `voice` | Acoustic Presence System. Piper-en-ryan-medium local TTS by default. Applies persona EQ + room-aware loudness from `mood`. | `voice.speak` | hardware |
| `observer` | Local-network web cockpit on `http://aegis.local:8080`. Anthropological / archival / reflective. Lets the dogfooder inspect Moments, replay days, edit Rules of Intervention live. | everything (mirror) | nothing |
| `keeper` | Maintenance. Nightly Moment consolidation, Ghost Moment lifecycle steps, theme reinforcement, embedding re-index, snapshot to NVMe. Runs only in Sleep. | `state.changed` | nothing |

### 4.3 Cognition routing

1. **Default = local Gemma 2B** (via Ollama). Handles temporal and routine continuity reflections.
2. **Escalate to Claude API when:**
   - Retrieval includes a cross-day Memory Magic Moment.
   - The user has just spoken and a response requires real understanding.
   - Local model self-reports low confidence (logprob threshold).
   - The Steward vetoed the local candidate and asked for a stronger one.
3. **All Claude calls pass a redaction layer.** Raw frames, raw audio, PII never leave. Only abstracted facts, persona context, and retrieved Moment summaries are sent. The Node's privacy posture is enforced in the cloud-egress path, not just in marketing.

Claude is *occasional higher-order cognition*, not the organism. The organism is pacing, memory, presence, restraint, continuity.

### 4.4 Repo layout

New repo `aegis-core/`. Not extended from `claude-ear`; that repo is React Native + iOS-bridged and architecturally wrong for a Linux desktop organism. Selected patterns may be ported (Claude integration patterns, persona prompt structure) but the architectural weight does not carry forward.

```
aegis-core/
  firmware/heartbeat/        # RP2040 (C / MicroPython)
  services/
    senses/                  # perception
    state/                   # presence state machine
    memory/                  # SQLite + sqlite-vss
    mood/                    # ambient mood
    mind/                    # local Gemma + Claude router
    steward/                 # intervention gate (the moat)
    voice/                   # Piper TTS + Acoustic Presence
    observer/                # local web cockpit (anthropological)
    keeper/                  # nightly maintenance
  personas/
    desk_companion.yaml      # the v1 persona
  rules/
    intervention.md          # the Rules of Intervention (human-editable, live-reloaded)
  hardware/
    shell/                   # F3D/STEP wedge files
    pcb/                     # carrier board KiCad
    bom.md
  ops/
    systemd/                 # service units
    snapshots/               # nightly memory backups
  docs/
    principles.md            # the design principles (mirrored)
    architecture.md          # this section, expanded
```

---

