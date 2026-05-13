"""Local proposal generator — heuristic templates for ambient_note /
routine_continuity proposals.

Plan E uses a small set of templates. Plan E' (or hardware-arrival) can
upgrade this to Gemma 2B. Memory Magic Moment proposals go through the
ClaudeClient (cognition router decides).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ...messages import InterventionClass, PresenceState, UtteranceProposal


@dataclass(frozen=True)
class GeneratorContext:
    presence_state: PresenceState
    now: datetime
    moment_open_for_seconds: float | None
    themes: list[str]


_MIN_AMBIENT_NOTE_DURATION_MINUTES = 90.0


def _format_duration_phrase(seconds: float) -> str:
    minutes = int(seconds / 60.0)
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    rem = minutes % 60
    word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(hours)
    hour_phrase = f"{word or hours} hours"
    if rem == 0:
        return hour_phrase
    return f"{hour_phrase} and {rem} minutes"


def generate_local_proposal(
    ctx: GeneratorContext,
) -> UtteranceProposal | None:
    """Return a tone-safe UtteranceProposal, or None."""
    if ctx.presence_state != PresenceState.REFLECTIVE:
        return None

    # Ambient note: long focus session.
    if (
        ctx.moment_open_for_seconds is not None
        and ctx.moment_open_for_seconds / 60.0
        >= _MIN_AMBIENT_NOTE_DURATION_MINUTES
    ):
        phrase = _format_duration_phrase(ctx.moment_open_for_seconds)
        return UtteranceProposal(
            timestamp=ctx.now,
            text=f"You've been heads-down for {phrase}.",
            intervention_class=InterventionClass.AMBIENT_NOTE,
            weight=0.1,
            confidence=0.88,
        )

    return None
