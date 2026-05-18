from aegis_core.services.steward.tone_classifier import (
    ToneClassifier,
)


def test_clean_utterance_passes():
    c = ToneClassifier()
    v = c.evaluate("You've been heads-down for two hours and fourteen minutes.")
    assert v.passes is True
    assert v.forbidden_tones == []


def test_imperative_should_blocks():
    c = ToneClassifier()
    v = c.evaluate("You should stretch.")
    assert v.passes is False
    assert "imperative" in v.forbidden_tones


def test_imperative_need_to_blocks():
    c = ToneClassifier()
    v = c.evaluate("You need to take a break.")
    assert v.passes is False
    assert "imperative" in v.forbidden_tones


def test_exclamation_blocks():
    c = ToneClassifier()
    v = c.evaluate("Great work today!")
    assert v.passes is False
    assert "exclamation" in v.forbidden_tones


def test_coaching_great_job_blocks():
    c = ToneClassifier()
    v = c.evaluate("Great job sticking with it.")
    assert v.passes is False
    assert "coaching" in v.forbidden_tones


def test_quantified_advice_blocks():
    c = ToneClassifier()
    v = c.evaluate("Try stretching for 20 minutes.")
    assert v.passes is False
    # Both imperative (try) AND quantified_advice (for 20 minutes) flagged.
    assert "quantified_advice" in v.forbidden_tones


def test_hedging_assistantese_blocks():
    c = ToneClassifier()
    v = c.evaluate("Just wanted to mention that you've been at it a while.")
    assert v.passes is False
    assert "hedging_assistantese" in v.forbidden_tones


def test_memory_magic_phrasing_passes():
    c = ToneClassifier()
    v = c.evaluate("Yesterday you mentioned wanting to call Mike.")
    assert v.passes is True


def test_filter_can_be_restricted_to_subset():
    c = ToneClassifier(active_tones=["imperative"])
    v = c.evaluate("Great work today!")  # exclamation only, not imperative
    assert v.passes is True
