from datetime import UTC, datetime

from aegis_core.messages import InterventionClass, PresenceState
from aegis_core.services.mind.local_generator import (
    GeneratorContext,
    generate_local_proposal,
)


def _ctx(
    presence_state: PresenceState = PresenceState.REFLECTIVE,
    moment_open_for_minutes: float | None = None,
    themes: list[str] | None = None,
) -> GeneratorContext:
    return GeneratorContext(
        presence_state=presence_state,
        now=datetime(2026, 5, 12, 10, 30, 0, tzinfo=UTC),
        moment_open_for_seconds=(
            moment_open_for_minutes * 60.0 if moment_open_for_minutes else None
        ),
        themes=list(themes or []),
    )


def test_no_proposal_outside_reflective():
    p = generate_local_proposal(_ctx(presence_state=PresenceState.ATTENTIVE))
    assert p is None


def test_ambient_note_when_long_focus_session():
    p = generate_local_proposal(_ctx(moment_open_for_minutes=134.0))
    assert p is not None
    assert p.intervention_class == InterventionClass.AMBIENT_NOTE
    # Phrasing must not be imperative.
    assert "you should" not in p.text.lower()
    assert "you need" not in p.text.lower()
    # Should reference the duration.
    assert "two hours" in p.text.lower() or "hours" in p.text.lower()


def test_no_proposal_when_no_context():
    p = generate_local_proposal(_ctx(moment_open_for_minutes=None))
    assert p is None


def test_short_session_does_not_produce_ambient_note():
    p = generate_local_proposal(_ctx(moment_open_for_minutes=5.0))
    assert p is None
