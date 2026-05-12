import json
from datetime import UTC, datetime, timedelta

from aegis_core.services.keeper.consolidation import classify_moment


def _moment(
    duration_s: float = 0.0,
    closed: bool = True,
    posture_events: int = 0,
    voice_events: int = 0,
    focus_score: float = 0.0,
    started_hours_ago: float = 1.0,
) -> dict:
    started = datetime.now(UTC) - timedelta(hours=started_hours_ago)
    ended = started + timedelta(seconds=duration_s) if closed else None
    return {
        "id": "moment_test",
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat() if ended else None,
        "type": "focus_session",
        "state": "tentative",
        "signature_json": json.dumps(
            {
                "posture_events": posture_events,
                "voice_events": voice_events,
                "focus_score": focus_score,
            }
        ),
    }


def test_consolidates_real_focus_session():
    m = _moment(duration_s=180, posture_events=12, focus_score=0.85)
    assert classify_moment(m) == "consolidated"


def test_consolidates_sustained_observation_even_without_focus():
    m = _moment(duration_s=120, posture_events=8, focus_score=0.3)
    assert classify_moment(m) == "consolidated"


def test_fades_too_short():
    m = _moment(duration_s=15, posture_events=2, focus_score=0.9)
    assert classify_moment(m) == "fading"


def test_fades_no_signal():
    m = _moment(duration_s=300, posture_events=0, voice_events=0)
    assert classify_moment(m) == "fading"


def test_fades_orphan_unclosed_old_moment():
    m = _moment(closed=False, started_hours_ago=48)
    assert classify_moment(m) == "fading"


def test_keeps_tentative_when_recent_and_ambiguous():
    # 60s duration, low focus, mild posture activity — too early to judge.
    # Should remain tentative pending more reinforcement, not auto-fade.
    m = _moment(duration_s=60, posture_events=2, focus_score=0.2)
    assert classify_moment(m) == "keep"
