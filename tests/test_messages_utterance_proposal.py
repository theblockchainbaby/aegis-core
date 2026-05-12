from datetime import UTC, datetime

import pytest

from aegis_core.messages import InterventionClass, UtteranceProposal


def test_utterance_proposal_roundtrip():
    msg = UtteranceProposal(
        timestamp=datetime.now(UTC),
        text="You've been heads-down for two hours.",
        intervention_class=InterventionClass.AMBIENT_NOTE,
        weight=0.1,
        confidence=0.9,
        context={"moment_id": "moment_test"},
    )
    assert UtteranceProposal.model_validate_json(msg.model_dump_json()) == msg


def test_utterance_proposal_default_empty_context():
    msg = UtteranceProposal(
        timestamp=datetime.now(UTC),
        text="hi",
        intervention_class=InterventionClass.AMBIENT_NOTE,
        weight=0.1,
        confidence=0.9,
    )
    assert msg.context == {}


def test_utterance_proposal_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        UtteranceProposal(
            timestamp=datetime.now(UTC),
            text="x",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=1.5,
        )


def test_utterance_proposal_rejects_negative_weight():
    with pytest.raises(ValueError):
        UtteranceProposal(
            timestamp=datetime.now(UTC),
            text="x",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=-0.5,
            confidence=0.9,
        )


def test_intervention_class_values():
    assert InterventionClass.AMBIENT_NOTE.value == "ambient_note"
    assert InterventionClass.ROUTINE_CONTINUITY.value == "routine_continuity"
    assert InterventionClass.MEMORY_MAGIC.value == "memory_magic"
    assert InterventionClass.EMOTIONAL_CHECK.value == "emotional_check"
