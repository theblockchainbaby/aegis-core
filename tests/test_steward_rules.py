from pathlib import Path

import pytest

from aegis_core.services.steward.rules import Rules, load_rules

REPO_RULES = (
    Path(__file__).resolve().parent.parent / "rules" / "intervention.yaml"
)


def test_load_rules_from_repo_yaml():
    rules = load_rules(REPO_RULES)
    assert isinstance(rules, Rules)
    assert rules.silence_budget.default_weight_per_day == 3.0
    assert rules.silence_budget.hard_cap_per_day == 5
    assert rules.confidence_threshold.default == 0.85
    assert "reflective" in rules.allowed_states_for_speech
    assert "imperative" in rules.forbidden_tones
    assert rules.intervention_weights["memory_magic"] == 1.0


def test_load_rules_rejects_missing_section(tmp_path: Path):
    p = tmp_path / "broken.yaml"
    p.write_text("silence_budget:\n  default_weight_per_day: 3.0\n")
    with pytest.raises(ValueError):
        load_rules(p)


def test_load_rules_rejects_malformed_yaml(tmp_path: Path):
    p = tmp_path / "broken.yaml"
    p.write_text("this: is: not: yaml: [")
    with pytest.raises(ValueError):
        load_rules(p)


def test_intervention_weight_for_returns_known_class():
    rules = load_rules(REPO_RULES)
    assert rules.weight_for("memory_magic") == 1.0
    assert rules.weight_for("ambient_note") == 0.1


def test_intervention_weight_for_unknown_class_raises():
    rules = load_rules(REPO_RULES)
    with pytest.raises(KeyError):
        rules.weight_for("unknown_class")
