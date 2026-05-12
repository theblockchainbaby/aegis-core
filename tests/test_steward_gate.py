from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis_core.messages import (
    InterventionClass,
    PresenceState,
    UtteranceProposal,
)
from aegis_core.services.steward.attention import (
    ProgrammableAttentionSignals,
    StubAttentionSignals,
)
from aegis_core.services.steward.clock import FakeClock
from aegis_core.services.steward.gate import GateState, evaluate
from aegis_core.services.steward.rules import load_rules
from aegis_core.services.steward.tone_classifier import ToneClassifier


REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


def _proposal(
    text: str = "Yesterday you mentioned the landing page.",
    intervention_class: InterventionClass = InterventionClass.MEMORY_MAGIC,
    weight: float = 1.0,
    confidence: float = 0.92,
) -> UtteranceProposal:
    return UtteranceProposal(
        timestamp=datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC),
        text=text,
        intervention_class=intervention_class,
        weight=weight,
        confidence=confidence,
    )


def _gate_state(
    presence_state: PresenceState = PresenceState.REFLECTIVE,
    silence_budget_remaining: float = 3.0,
    utterances_today: int = 0,
    last_utterance_at: datetime | None = None,
    presence_decay_multiplier: float = 1.0,
    scar_tissue_penalty: float = 0.0,
    recovery_threshold_bump: float = 0.0,
) -> GateState:
    return GateState(
        presence_state=presence_state,
        silence_budget_remaining=silence_budget_remaining,
        utterances_today=utterances_today,
        last_utterance_at=last_utterance_at,
        presence_decay_multiplier=presence_decay_multiplier,
        scar_tissue_penalty=scar_tissue_penalty,
        recovery_threshold_bump=recovery_threshold_bump,
    )


def _ctx():
    return {
        "rules": load_rules(REPO_RULES),
        "tone": ToneClassifier(),
        "signals": StubAttentionSignals(),
        "clock": FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC)),
    }


def test_clean_proposal_in_reflective_proceeds():
    d = evaluate(_proposal(), _gate_state(), **_ctx())
    assert d.proceed is True
    assert d.reasons == []


def test_wrong_state_vetoes():
    d = evaluate(
        _proposal(),
        _gate_state(presence_state=PresenceState.OBSERVING),
        **_ctx(),
    )
    assert d.proceed is False
    assert "wrong_state" in d.reasons


def test_low_confidence_vetoes():
    d = evaluate(
        _proposal(confidence=0.70),
        _gate_state(),
        **_ctx(),
    )
    assert d.proceed is False
    assert "confidence_below_threshold" in d.reasons


def test_scar_tissue_raises_threshold():
    # confidence=0.86 passes baseline (0.85) but fails with 0.05 scar.
    d = evaluate(
        _proposal(confidence=0.86),
        _gate_state(scar_tissue_penalty=0.05),
        **_ctx(),
    )
    assert d.proceed is False
    assert "confidence_below_threshold" in d.reasons


def test_recovery_threshold_bump_raises_threshold():
    d = evaluate(
        _proposal(confidence=0.90),
        _gate_state(recovery_threshold_bump=0.08),
        **_ctx(),
    )
    assert d.proceed is False
    assert "confidence_below_threshold" in d.reasons


def test_insufficient_budget_vetoes():
    d = evaluate(
        _proposal(weight=1.0),
        _gate_state(silence_budget_remaining=0.5),
        **_ctx(),
    )
    assert d.proceed is False
    assert "silence_budget_exhausted" in d.reasons


def test_daily_cap_vetoes():
    d = evaluate(
        _proposal(),
        _gate_state(utterances_today=5),
        **_ctx(),
    )
    assert d.proceed is False
    assert "daily_cap_reached" in d.reasons


def test_hourly_cap_vetoes():
    now = datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC)
    d = evaluate(
        _proposal(),
        _gate_state(last_utterance_at=now),
        rules=load_rules(REPO_RULES),
        tone=ToneClassifier(),
        signals=StubAttentionSignals(),
        clock=FakeClock(datetime(2026, 5, 12, 9, 30, 0, tzinfo=UTC)),
    )
    assert d.proceed is False
    assert "hourly_cap_reached" in d.reasons


def test_typing_vetoes_competing_for_attention():
    sig = ProgrammableAttentionSignals()
    sig.set_typing(True)
    ctx = _ctx()
    ctx["signals"] = sig
    d = evaluate(_proposal(), _gate_state(), **ctx)
    assert d.proceed is False
    assert "competing_for_attention" in d.reasons


def test_short_pause_vetoes_competing_for_attention():
    sig = ProgrammableAttentionSignals()
    sig.set_seconds_since_last_pause(1.0)  # below the 4s rule
    ctx = _ctx()
    ctx["signals"] = sig
    d = evaluate(_proposal(), _gate_state(), **ctx)
    assert d.proceed is False
    assert "competing_for_attention" in d.reasons


def test_forbidden_tone_vetoes():
    d = evaluate(
        _proposal(text="You should take a break."),
        _gate_state(),
        **_ctx(),
    )
    assert d.proceed is False
    assert any(r.startswith("forbidden_tone") for r in d.reasons)


def test_weight_cost_includes_presence_decay_multiplier():
    d = evaluate(
        _proposal(weight=1.0),
        _gate_state(presence_decay_multiplier=1.10),
        **_ctx(),
    )
    assert d.proceed is True
    # weight_cost is what gets deducted from the budget — should be > 1.0.
    assert d.weight_cost == pytest.approx(1.10)


def test_multiple_failures_listed_in_strict_precedence_order():
    """Veto precedence is contractual. Lock the exact order with strict equality.

    Reasons triggered by this proposal (in canonical order):
      - confidence_below_threshold  (confidence=0.70 < 0.85 baseline)
      - silence_budget_exhausted   (budget_remaining=0.0)
      - forbidden_tone:imperative  ("You should …")
      - competing_for_attention    (typing=True)

    NOT triggered: wrong_state, daily_cap_reached, hourly_cap_reached.
    """
    sig = ProgrammableAttentionSignals()
    sig.set_typing(True)
    ctx = _ctx()
    ctx["signals"] = sig
    d = evaluate(
        _proposal(confidence=0.70, text="You should rest."),
        _gate_state(silence_budget_remaining=0.0),
        **ctx,
    )
    assert d.proceed is False
    assert d.reasons == [
        "confidence_below_threshold",
        "silence_budget_exhausted",
        "forbidden_tone:imperative",
        "competing_for_attention",
    ]


def test_all_check_failures_in_contractual_order():
    """Drive every check to fail. Lock the full precedence prefix."""
    sig = ProgrammableAttentionSignals()
    sig.set_typing(True)
    now_test = datetime(2026, 5, 12, 9, 30, 0, tzinfo=UTC)
    d = evaluate(
        _proposal(confidence=0.50, text="You should take a break for 20 minutes!"),
        _gate_state(
            presence_state=PresenceState.OBSERVING,  # wrong_state
            silence_budget_remaining=0.0,            # silence_budget_exhausted
            utterances_today=10,                     # daily_cap_reached
            last_utterance_at=datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC),  # hourly_cap_reached
        ),
        rules=load_rules(REPO_RULES),
        tone=ToneClassifier(),
        signals=sig,                                 # competing_for_attention
        clock=FakeClock(now_test),
    )
    assert d.proceed is False
    # First five reasons MUST be in this exact order (the contractual prefix).
    assert d.reasons[:5] == [
        "wrong_state",
        "confidence_below_threshold",
        "silence_budget_exhausted",
        "daily_cap_reached",
        "hourly_cap_reached",
    ]
    # Forbidden tones come AFTER the numbered checks and BEFORE
    # competing_for_attention. The internal order of forbidden_tone:* entries
    # follows the classifier's iteration over `_active`.
    tone_entries = [r for r in d.reasons if r.startswith("forbidden_tone:")]
    assert tone_entries, "expected at least one forbidden_tone:* reason"
    first_tone_index = d.reasons.index(tone_entries[0])
    assert first_tone_index == 5
    # competing_for_attention is always last when present.
    assert d.reasons[-1] == "competing_for_attention"
