import asyncio

import pytest

from aegis_core.services.mind.claude_client import ClaudeClient, StubClaudeClient


@pytest.mark.asyncio
async def test_stub_claude_returns_text():
    c = StubClaudeClient()
    out = await c.complete(
        system="You are Aegis Core.",
        user="A Moment summary about the landing page redesign.",
    )
    assert isinstance(out, str)
    assert len(out) > 0


@pytest.mark.asyncio
async def test_stub_claude_uses_input_for_canned_output():
    c = StubClaudeClient()
    out = await c.complete(
        system="You are Aegis Core.",
        user="moment_summary: landing page redesign",
    )
    # The stub should echo SOMETHING from the input back in a non-imperative
    # phrasing. Memory-magic phrasing should start with "Yesterday you" or
    # similar — see the implementation.
    assert "landing" in out.lower() or "yesterday" in out.lower()


def test_stub_satisfies_protocol():
    assert isinstance(StubClaudeClient(), ClaudeClient)
