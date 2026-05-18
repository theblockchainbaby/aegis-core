"""Steward gate — pure arithmetic, deterministic.

Given a proposal and the surrounding state, return a Decision. No I/O, no
side effects. Every input is explicit. This is the most carefully-tested
module in the repo because it IS the moat.

## Veto precedence (CONTRACTUAL)

The order in which veto reasons are appended to Decision.reasons is part
of the public contract. Downstream consumers — observer log readers,
future learned scar-tissue attribution, intervention-log analytics, test
fixtures — read `reasons[0]` as the *primary* veto cause. Reshuffling
silently would corrupt that attribution.

The order is:

  1. wrong_state
  2. confidence_below_threshold
  3. silence_budget_exhausted
  4. daily_cap_reached
  5. hourly_cap_reached
  6. forbidden_tone:* (one entry per detected tone, in classifier order)
  7. competing_for_attention

DO NOT reshuffle the existing checks. New veto reasons may be added but
only at positions that preserve this prefix's semantics. The evaluation
function below performs the checks in this exact order; the `reasons`
list accumulates left-to-right.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from ...messages import PresenceState, UtteranceProposal
from .attention import AttentionSignals
from .clock import Clock
from .tone_classifier import ToneClassifier

if TYPE_CHECKING:
    from .rules import Rules


@dataclass(frozen=True)
class GateState:
    """Steward-internal state at the moment of evaluation."""

    presence_state: PresenceState
    silence_budget_remaining: float
    utterances_today: int
    last_utterance_at: datetime | None
    presence_decay_multiplier: float = 1.0
    scar_tissue_penalty: float = 0.0
    recovery_threshold_bump: float = 0.0


@dataclass(frozen=True)
class Decision:
    proceed: bool
    reasons: list[str] = field(default_factory=list)
    weight_cost: float = 0.0


def evaluate(
    proposal: UtteranceProposal,
    state: GateState,
    *,
    rules: Rules,
    tone: ToneClassifier,
    signals: AttentionSignals,
    clock: Clock,
) -> Decision:
    reasons: list[str] = []

    # 1. State must permit speech.
    allowed = {s.lower() for s in rules.allowed_states_for_speech}
    if state.presence_state.value not in allowed:
        reasons.append("wrong_state")

    # 2. Effective confidence threshold.
    effective_threshold = (
        rules.confidence_threshold.reflective_state
        + state.scar_tissue_penalty
        + state.recovery_threshold_bump
    )
    if proposal.confidence < effective_threshold:
        reasons.append("confidence_below_threshold")

    # 3. Silence budget.
    weight_cost = proposal.weight * state.presence_decay_multiplier
    if state.silence_budget_remaining < weight_cost:
        reasons.append("silence_budget_exhausted")

    # 4. Daily cap.
    if state.utterances_today >= rules.silence_budget.hard_cap_per_day:
        reasons.append("daily_cap_reached")

    # 5. Hourly cap — must be > 1 hour / hard_cap_per_hour since last utterance.
    if (
        state.last_utterance_at is not None
        and (clock.now() - state.last_utterance_at)
        < timedelta(hours=1) * (1.0 / rules.silence_budget.hard_cap_per_hour)
    ):
        reasons.append("hourly_cap_reached")

    # 6. Tone classifier (one entry per detected tone, in classifier order).
    verdict = tone.evaluate(proposal.text)
    if not verdict.passes:
        for t in verdict.forbidden_tones:
            reasons.append(f"forbidden_tone:{t}")

    # 7. Competing for attention.
    cfa = rules.competing_for_attention_checks
    competing = False
    if cfa.block_during_active_typing and signals.is_typing():
        competing = True
    if cfa.block_during_active_call and signals.is_in_call():
        competing = True
    if cfa.block_during_video_playback and signals.is_video_playing():
        competing = True
    if (
        signals.seconds_since_last_pause()
        < cfa.min_natural_pause_seconds_before_speech
    ):
        competing = True
    if competing:
        reasons.append("competing_for_attention")

    return Decision(
        proceed=(not reasons),
        reasons=reasons,
        weight_cost=weight_cost,
    )
