from datetime import UTC, datetime

from aegis_core.services.steward.clock import FakeClock
from aegis_core.services.steward.decay import PresenceDecay


def test_no_decay_when_recent():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    d = PresenceDecay(
        clock=c,
        window_days=7,
        low_engagement_threshold_per_week=2,
        multiplier_per_step=1.05,
        floor=1.5,
        baseline_budget=3.0,
    )
    assert d.multiplier() == 1.0


def test_step_applied_after_one_low_engagement_week():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    d = PresenceDecay(
        clock=c,
        window_days=7,
        low_engagement_threshold_per_week=2,
        multiplier_per_step=1.05,
        floor=1.5,
        baseline_budget=3.0,
    )
    # Simulate one week of zero acknowledged utterances.
    c.advance(seconds=8 * 86400)
    d.tick(acknowledged_this_window=0)
    assert d.multiplier() == 1.05


def test_engagement_resets_decay():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    d = PresenceDecay(
        clock=c,
        window_days=7,
        low_engagement_threshold_per_week=2,
        multiplier_per_step=1.05,
        floor=1.5,
        baseline_budget=3.0,
    )
    c.advance(seconds=8 * 86400)
    d.tick(acknowledged_this_window=0)
    assert d.multiplier() == 1.05
    c.advance(seconds=8 * 86400)
    d.tick(acknowledged_this_window=3)  # engaged again
    assert d.multiplier() == 1.0


def test_budget_floor_respected():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    d = PresenceDecay(
        clock=c,
        window_days=7,
        low_engagement_threshold_per_week=2,
        multiplier_per_step=2.0,  # extreme for the test
        floor=1.5,
        baseline_budget=3.0,
    )
    for _ in range(10):
        c.advance(seconds=8 * 86400)
        d.tick(acknowledged_this_window=0)
    # 3.0 / 1.5 floor means max multiplier is 2.0; clamped.
    assert d.effective_budget() >= 1.5
