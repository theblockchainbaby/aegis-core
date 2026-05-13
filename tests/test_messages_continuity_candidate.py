from datetime import UTC, datetime

import pytest

from aegis_core.messages import ContinuityCandidate, InterventionClass


def test_continuity_candidate_roundtrip():
    msg = ContinuityCandidate(
        timestamp=datetime.now(UTC),
        moment_id="moment_2026-05-11T09-14_focus_session_abc123",
        moment_summary="Long focused session on the landing page redesign.",
        themes=["landing", "redesign"],
        confidence=0.88,
        suggested_class=InterventionClass.MEMORY_MAGIC,
    )
    assert ContinuityCandidate.model_validate_json(msg.model_dump_json()) == msg


def test_continuity_candidate_default_themes_empty():
    msg = ContinuityCandidate(
        timestamp=datetime.now(UTC),
        moment_id="x",
        moment_summary="y",
        confidence=0.9,
        suggested_class=InterventionClass.MEMORY_MAGIC,
    )
    assert msg.themes == []


def test_continuity_candidate_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        ContinuityCandidate(
            timestamp=datetime.now(UTC),
            moment_id="x",
            moment_summary="y",
            confidence=1.5,
            suggested_class=InterventionClass.MEMORY_MAGIC,
        )
