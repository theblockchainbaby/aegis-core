"""Consolidation rules — pure function from Moment row → classification.

A tentative Moment that's gone through nightly consolidation becomes either
'consolidated' (durable; survives to the long-term memory layer) or
'fading' (decays naturally, deleted after FADE_LIFETIME_DAYS). Some Moments
are kept tentative — too short or ambiguous to judge yet, but with some
signal worth waiting on (Ghost Moment psychology).

Rules are deliberate, simple, and tunable. The 90-day dogfood phase is for
adjusting these thresholds based on what feels right in the observer log.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

MIN_DURATION_S_FOR_CONSOLIDATE = 30.0
FOCUS_THRESHOLD = 0.5
SUSTAINED_POSTURE_EVENTS = 5
ORPHAN_TIMEOUT_H = 24.0
FADE_LIFETIME_DAYS = 7.0


def _duration_s(row: dict) -> float:
    started = datetime.fromisoformat(row["started_at_utc"])
    if row.get("ended_at_utc"):
        ended = datetime.fromisoformat(row["ended_at_utc"])
        return (ended - started).total_seconds()
    return -1.0  # unclosed


def _started_age_hours(row: dict) -> float:
    started = datetime.fromisoformat(row["started_at_utc"])
    now = datetime.now(UTC)
    return (now - started).total_seconds() / 3600.0


def classify_moment(row: dict) -> str:
    """Return 'consolidated', 'fading', or 'keep' (= leave tentative)."""
    duration = _duration_s(row)
    sig = json.loads(row.get("signature_json") or "{}")
    posture_events = int(sig.get("posture_events", 0))
    voice_events = int(sig.get("voice_events", 0))
    focus_score = float(sig.get("focus_score", 0.0))

    # Orphan: never closed and older than orphan timeout
    if duration < 0 and _started_age_hours(row) > ORPHAN_TIMEOUT_H:
        return "fading"

    # Unclosed but still recent: leave it
    if duration < 0:
        return "keep"

    # Too short
    if duration < MIN_DURATION_S_FOR_CONSOLIDATE:
        return "fading"

    # No signal
    if posture_events == 0 and voice_events == 0:
        return "fading"

    # Real focus session
    if focus_score >= FOCUS_THRESHOLD and duration >= 60.0:
        return "consolidated"

    # Sustained observation
    if posture_events >= SUSTAINED_POSTURE_EVENTS:
        return "consolidated"

    # Still recent and ambiguous → leave tentative; let it accumulate more
    # reinforcement before we decay it. This matches Ghost Moment psychology:
    # short observations get a chance to become something before fading.
    if duration < 300 and posture_events >= 1:
        return "keep"

    return "fading"
