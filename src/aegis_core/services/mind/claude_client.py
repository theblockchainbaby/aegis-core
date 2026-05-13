"""ClaudeClient — abstract interface for the cognition escalation path.

Plan E ships a Stub that returns canned, tone-classifier-friendly text
derived from the input. Plan E' swaps this for a real AnthropicClient
without changing call sites.
"""
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClaudeClient(Protocol):
    async def complete(self, *, system: str, user: str) -> str: ...


class StubClaudeClient:
    """Deterministic stub. Generates Memory-Magic-Moment-style phrasing
    from the user message. No randomness; no API calls; passes the Plan D
    forbidden-tone classifier.
    """

    async def complete(self, *, system: str, user: str) -> str:
        # Extract a short theme word from the input — first non-stopword.
        # This is enough to prove the wiring; Plan E' replaces with real
        # Claude.
        words = re.findall(r"[A-Za-z][A-Za-z\-]+", user)
        candidates = [
            w for w in words
            if w.lower() not in {
                "moment", "summary", "the", "a", "an", "and", "or",
                "of", "in", "on", "to", "is", "was", "for", "with",
                "you", "your", "user", "session", "long", "focused",
            }
            and len(w) > 2
        ]
        if candidates:
            theme = candidates[0].lower()
            return f"Yesterday you mentioned the {theme}."
        return "Yesterday you were here."
