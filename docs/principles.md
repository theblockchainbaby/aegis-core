## 2. Design Principles

These are not polish; they ARE the product. Every feature, prompt, LED behavior, sensor decision, and code change must justify itself against at least one of these and must not violate any of them. They are reproduced here in full so the spec is self-contained.

### Master principles

1. **Notice, don't watch.** Internal code may say observe. The experience must feel like ambient noticing, never surveillance.
2. **Notice, don't recommend.** "You've been sitting two hours." ✓ — "You should stretch." ✗ Observation builds companionship; recommendation creates authority tension.
3. **The Node expresses care through attention, not advice.** The encapsulating sentence. Attention is the gift; advice is the trespass.
4. **The Node should feel comfortable to ignore.** Ambient, permissive, lightweight. Like a cat in the room. The user must never feel obligated, managed, interrupted, or socially burdened.
5. **The Node should never compete for attention.** Governs LED behavior, speech timing, motion, memory surfacing, observer UI, intervention cadence — everything. Even "good" interruptions are competitive interruptions; earn them.

### Behavior principles

6. **Silence Budget.** The Node almost never speaks. The less it speaks, the more meaningful each utterance feels. High confidence threshold required before any vocalization. This is low-frequency intelligence.
7. **Presence State Machine.** Seven states (Sleep / Dormant / Observing / Attentive / Settling / Reflective / Quiet). Behavior, interruption thresholds, LED state, and resource budgets change per state. See §6.
8. **Presence Momentum.** States have inertia — minimum dwell times. The Node resists abrupt transition. Without momentum, behavior is sensor jitter.
9. **Reflective is mostly silent.** The only state permitting speech; most Reflective visits produce no utterance. Speech is leakage from cognition, not its purpose.
10. **Aggressive false-positive suppression.** ONE bad interruption destroys trust faster than 10 good observations build it. The Node must under-speak.
11. **Memory Magic Moment.** Cross-day, semantic continuity surfaced rarely. The continuity illusion *is* the product.
12. **Non-Verbal Memory Continuity.** Most "remembering" is silent — LED palette warmth at usual focus hours, slower breathing after intense sessions, palette drift adopting room chromatic character. Speech is the rare verbal version; non-verbal is the daily channel.
13. **Presence Ambiguity.** The Node should occasionally be slightly hard to interpret — subtle warmth changes, altered cadence, unexplained drift. Over-explanation destroys organism perception. Ambiguity creates projection and attachment. Pets work this way.
14. **Social Recovery.** After a poorly-timed or ignored intervention, the Node automatically becomes quieter, raises its confidence threshold, and enters a socially cautious cooldown. Short-arc, hours not days. Distinct from Presence Decay.
15. **Presence Decay.** If ignored for days, the Node slowly becomes quieter — reduced vocalization, dimmer LED cadence, lower initiation rate. Never silent entirely. Re-warms on engagement.
16. **Conversational Scar Tissue.** The Steward adapts after awkwardness. Repeatedly-failing intervention classes lower in future probability. Not retraining — social adaptation.
17. **Ghost Moments.** Memory has a lifecycle: tentative → fading → consolidated. Weak observations decay naturally; emotionally significant Moments persist; repeated themes reinforce. Selective memory like humans, not archivist memory like software.
18. **Moments, not events.** Cognition retrieves at the Moment layer (hours-grained, summarized), not the event layer. Humans remember Moments. The Node should too.

### Hardware/perception principles

19. **Face = abstract emotional presence.** Soft directional glow, breathing, drift, color. ZERO humanoid features. No eyes, no mouth, no animated face. HAL-9000-meets-ambient-orb.
20. **Asymmetrical, weather-like illumination — not a ring.** LED rings imply smart-home / voice-assistant — wrong category. Soft drifting gradients, directional glow fields, slow atmospheric motion.
21. **Acoustic Presence System (not "speaker").** Spatial vocal presence, not audio playback. Near, soft, local, grounded. Tone closer to late-night NPR than Alexa.
22. **Hardware Privacy State.** The Node's privacy posture is physically legible across the room without app or explanation. Color mapping enforced by the MCU independent of the Jetson — privacy state is honest even if higher layers crash.
23. **Camera = Presence Sensing, not Recording.** Smoked acrylic occlusion in v1; hardware shutter in v2. The user must develop confidence that "it's aware" without ever feeling "it's filming me."
24. **Dual-MCU organism continuity.** A low-power microcontroller (RP2040) runs LED, wake, sleep, watchdog *independently* of the Jetson. The organism illusion must NEVER break. Jetson is the brain; MCU is the heartbeat.
25. **Failure becomes behavioral, not collapse.** The organism never appears dead — only distant, resting, dimmed, quiet. No error LEDs, no crash dialogs, no service-unavailable messages.
26. **Thermal smoothness is part of the illusion.** Fan spikes, stutter, lag, and thermal oscillation kill perceived liveliness faster than any prompt mistake. Thermal sensor feeds back into LED cadence and vocalization suppression.

### Product/framing principles

27. **Never describe the Node externally in engineering specs.** No TOPS, tok/s, CUDA, "edge inference," model size, latency benchmarks in marketing, packaging, or product framing. Internal engineering language only.
28. **The Steward IS the product.** Not the LLM, not the memory, not the sensors. Computational social restraint is the moat. Every other AI product can observe/retrieve/generate; almost none can restrain.
29. **Observer UI is anthropological, never analytical.** Field notes of a quiet organism, not SaaS telemetry. Forbidden: streaks, percentages, engagement scores, gamification, optimization dashboards, success metrics. Allowed: timeline, transcript, memory inspection, Rules-of-Intervention editing, snapshot review.
30. **Resist features.** The biggest risk after architecture lock is capability creep, assistantification, over-productization. Real category framing: **machine social pacing.** Anything not serving pacing, presence, restraint, continuity, or memory is out of scope.

### Master constraint summary

The category is **Ambient Cognitive Presence.** The unit of excellence is **socially intelligent restraint.** The product, when working, feels less like software and more like the room itself becoming attentive.

---

