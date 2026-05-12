"""Rules of Intervention — YAML loader + Pydantic schema.

Plan D loads at service startup. Hot reload (inotify / FSEvents) is Plan F.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SilenceBudget(_Strict):
    default_weight_per_day: float = Field(gt=0.0)
    refill_rate_weight: float = Field(gt=0.0)
    refill_rate_window_hours: float = Field(gt=0.0)
    hard_cap_per_hour: int = Field(ge=1)
    hard_cap_per_day: int = Field(ge=1)


class ConfidenceThreshold(_Strict):
    default: float = Field(ge=0.0, le=1.0)
    reflective_state: float = Field(ge=0.0, le=1.0)
    social_recovery_window: float = Field(ge=0.0, le=1.0)
    presence_decay_multiplier_per_week: float = Field(ge=1.0)


class CompetingForAttentionChecks(_Strict):
    block_during_active_typing: bool
    block_during_active_call: bool
    block_during_video_playback: bool
    min_natural_pause_seconds_before_speech: float = Field(ge=0.0)


class SocialRecoveryTrigger(_Strict):
    utterance_unacknowledged_for_seconds: float = Field(ge=0.0)
    user_negative_response_detected: bool
    user_explicitly_silenced: bool


class SocialRecoveryEffects(_Strict):
    confidence_threshold_bump: float = Field(ge=0.0, le=1.0)
    cooldown_state: str
    cooldown_duration_minutes: float = Field(ge=0.0)


class SocialRecovery(_Strict):
    trigger: SocialRecoveryTrigger
    effects: SocialRecoveryEffects


class PresenceDecayEffects(_Strict):
    silence_budget_reduction: float = Field(ge=0.0)
    led_warmth_reduction_pct: float = Field(ge=0.0)
    breath_cadence_slowdown_seconds: float = Field(ge=0.0)


class PresenceDecayFloor(_Strict):
    silence_budget_min: float = Field(ge=0.0)


class PresenceDecay(_Strict):
    measurement_window_days: int = Field(ge=1)
    low_engagement_threshold_per_week: int = Field(ge=0)
    effects_per_step: PresenceDecayEffects
    floor: PresenceDecayFloor


class ConversationalScarTissue(_Strict):
    track_per_intervention_class: bool
    vetoed_repeat_penalty: float = Field(ge=0.0)
    unacknowledged_repeat_penalty: float = Field(ge=0.0)
    recovery_on_acknowledgment: float = Field(ge=0.0)
    floor: float = Field(ge=0.0)
    cap: float = Field(ge=0.0)


class Rules(_Strict):
    silence_budget: SilenceBudget
    confidence_threshold: ConfidenceThreshold
    intervention_weights: dict[str, float]
    allowed_states_for_speech: list[str]
    forbidden_tones: list[str]
    forbidden_topics_v1: list[str]
    competing_for_attention_checks: CompetingForAttentionChecks
    social_recovery: SocialRecovery
    presence_decay: PresenceDecay
    conversational_scar_tissue: ConversationalScarTissue

    def weight_for(self, intervention_class: str) -> float:
        if intervention_class not in self.intervention_weights:
            raise KeyError(f"unknown intervention class: {intervention_class!r}")
        return self.intervention_weights[intervention_class]


def load_rules(path: str | Path) -> Rules:
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise ValueError(f"malformed YAML in {p}: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError(f"rules file {p} did not parse to a mapping")
    try:
        return Rules.model_validate(raw)
    except ValidationError as e:
        raise ValueError(f"rules schema validation failed in {p}: {e}") from e
