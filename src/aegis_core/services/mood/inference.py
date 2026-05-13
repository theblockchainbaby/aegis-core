"""Mood inference — state + signals → palette/cadence/warmth (pure logic).

Plan E uses state alone for the primary mapping. Plan E' will weave in
focus score, presence decay, social recovery, scar tissue, etc.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...messages import MoodChanged, Palette, PresenceState


@dataclass(frozen=True)
class MoodSignals:
    focus_score: float = 0.0
    social_recovery_active: bool = False
    presence_decay_multiplier: float = 1.0


_PALETTE_BY_STATE: dict[PresenceState, Palette] = {
    PresenceState.SLEEP: Palette.SLEEP,
    PresenceState.DORMANT: Palette.DORMANT_BLUE,
    PresenceState.OBSERVING: Palette.OBSERVING_DRIFT,
    PresenceState.ATTENTIVE: Palette.ATTENTIVE_WARM,
    PresenceState.SETTLING: Palette.SETTLING_REGRESS,
    PresenceState.REFLECTIVE: Palette.REFLECTIVE_VIOLET,
    PresenceState.QUIET: Palette.QUIET_COOL,
}

_CADENCE_BY_STATE: dict[PresenceState, float] = {
    PresenceState.SLEEP: 12.0,
    PresenceState.DORMANT: 7.5,
    PresenceState.OBSERVING: 6.0,
    PresenceState.ATTENTIVE: 5.5,
    PresenceState.SETTLING: 6.5,
    PresenceState.REFLECTIVE: 5.0,
    PresenceState.QUIET: 8.0,
}

_WARMTH_BY_STATE: dict[PresenceState, float] = {
    PresenceState.SLEEP: 0.05,
    PresenceState.DORMANT: 0.10,
    PresenceState.OBSERVING: 0.35,
    PresenceState.ATTENTIVE: 0.70,
    PresenceState.SETTLING: 0.55,
    PresenceState.REFLECTIVE: 0.65,
    PresenceState.QUIET: 0.20,
}


def infer_mood(
    *, state: PresenceState, signals: MoodSignals
) -> MoodChanged:
    palette = _PALETTE_BY_STATE.get(state, Palette.DORMANT_BLUE)
    cadence = _CADENCE_BY_STATE.get(state, 6.0)
    warmth = _WARMTH_BY_STATE.get(state, 0.3)

    # Deep-focus signature: high focus_score in Attentive slows breath +
    # adds warmth. Caps respected.
    if state == PresenceState.ATTENTIVE and signals.focus_score > 0.0:
        cadence = min(cadence + 0.7 * signals.focus_score, 7.0)
        warmth = min(warmth + 0.15 * signals.focus_score, 1.0)

    # Social recovery: cool the palette + slow the breath.
    if signals.social_recovery_active:
        cadence = min(cadence + 1.5, 10.0)
        warmth = max(warmth - 0.2, 0.0)

    # Presence decay: dim warmth proportional to multiplier above 1.0.
    if signals.presence_decay_multiplier > 1.0:
        warmth = max(
            warmth * (1.0 / signals.presence_decay_multiplier),
            0.0,
        )

    # The MoodChanged event carries the timestamp; this pure function
    # constructs it with `now` — the service caller can override if it
    # wants event-time semantics.
    from datetime import UTC, datetime

    return MoodChanged(
        timestamp=datetime.now(UTC),
        palette=palette,
        breath_cadence_seconds=cadence,
        warmth=warmth,
        reason=f"state_{state.value}",
    )
