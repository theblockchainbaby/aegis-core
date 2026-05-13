from datetime import UTC, datetime

import pytest

from aegis_core.messages import (
    ContinuityCandidate,
    InterventionClass,
    PresenceState,
)
from aegis_core.services.mind.claude_client import StubClaudeClient
from aegis_core.services.mind.local_generator import GeneratorContext
from aegis_core.services.mind.router import route


def _candidate() -> ContinuityCandidate:
    return ContinuityCandidate(
        timestamp=datetime(2026, 5, 12, 10, 30, 0, tzinfo=UTC),
        moment_id="moment_test",
        moment_summary="Long focused session on the landing page redesign.",
        themes=["landing", "redesign"],
        confidence=0.88,
        suggested_class=InterventionClass.MEMORY_MAGIC,
    )


def _gen_ctx(state=PresenceState.REFLECTIVE, moment_minutes=None):
    return GeneratorContext(
        presence_state=state,
        now=datetime(2026, 5, 12, 10, 30, 0, tzinfo=UTC),
        moment_open_for_seconds=(
            moment_minutes * 60.0 if moment_minutes else None
        ),
        themes=[],
    )


@pytest.mark.asyncio
async def test_router_escalates_to_claude_on_continuity_candidate():
    p = await route(
        gen_ctx=_gen_ctx(),
        candidate=_candidate(),
        claude=StubClaudeClient(),
    )
    assert p is not None
    assert p.intervention_class == InterventionClass.MEMORY_MAGIC
    assert "landing" in p.text.lower() or "yesterday" in p.text.lower()


@pytest.mark.asyncio
async def test_router_uses_local_when_no_candidate():
    p = await route(
        gen_ctx=_gen_ctx(moment_minutes=120),
        candidate=None,
        claude=StubClaudeClient(),
    )
    assert p is not None
    assert p.intervention_class == InterventionClass.AMBIENT_NOTE


@pytest.mark.asyncio
async def test_router_returns_none_when_neither_path_fires():
    # No candidate, and not in reflective → no local proposal either.
    p = await route(
        gen_ctx=_gen_ctx(state=PresenceState.ATTENTIVE),
        candidate=None,
        claude=StubClaudeClient(),
    )
    assert p is None
