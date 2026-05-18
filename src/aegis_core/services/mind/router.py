"""Cognition router — decides local vs Claude escalation per proposal.

Plan E rule: ContinuityCandidate in context → Claude (Memory Magic).
Otherwise → local heuristic generator.
"""
from __future__ import annotations

from datetime import UTC, datetime

from ...messages import (
    ContinuityCandidate,
    InterventionClass,
    UtteranceProposal,
)
from .claude_client import ClaudeClient
from .local_generator import GeneratorContext, generate_local_proposal
from .redaction import redact_for_cloud

_MEMORY_MAGIC_WEIGHT = 1.0


async def route(
    *,
    gen_ctx: GeneratorContext,
    candidate: ContinuityCandidate | None,
    claude: ClaudeClient,
) -> UtteranceProposal | None:
    if candidate is not None:
        # Memory Magic Moment path.
        redacted = redact_for_cloud(
            {
                "moment_summary": candidate.moment_summary,
                "themes": list(candidate.themes),
                "intervention_class": "memory_magic",
                "confidence": candidate.confidence,
            }
        )
        # Build a short user-message string from the redacted bundle.
        user_msg = f"moment_summary: {redacted.get('moment_summary', '')}"
        text = await claude.complete(
            system=(
                "You are Aegis Core, a quiet desk companion. Phrase the "
                "moment as a non-imperative observation. Never use 'you "
                "should' or exclamation."
            ),
            user=user_msg,
        )
        return UtteranceProposal(
            timestamp=datetime.now(UTC),
            text=text,
            intervention_class=InterventionClass.MEMORY_MAGIC,
            weight=_MEMORY_MAGIC_WEIGHT,
            confidence=candidate.confidence,
            context={"moment_id": candidate.moment_id},
        )

    return generate_local_proposal(gen_ctx)
