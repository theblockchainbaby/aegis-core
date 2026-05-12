from datetime import UTC, datetime

from aegis_core.services.steward.clock import FakeClock
from aegis_core.services.steward.recovery import SocialRecovery


def test_no_recovery_when_no_outstanding_utterance():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    r = SocialRecovery(
        clock=c,
        timeout_seconds=60,
        confidence_bump=0.08,
        cooldown_minutes=45,
    )
    assert r.is_active() is False
    assert r.threshold_bump() == 0.0


def test_unack_after_timeout_engages_recovery():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    r = SocialRecovery(
        clock=c,
        timeout_seconds=60,
        confidence_bump=0.08,
        cooldown_minutes=45,
    )
    r.note_utterance(class_="memory_magic")
    c.advance(seconds=61)
    r.tick()
    assert r.is_active() is True
    assert abs(r.threshold_bump() - 0.08) < 1e-6


def test_acknowledgment_clears_outstanding():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    r = SocialRecovery(
        clock=c,
        timeout_seconds=60,
        confidence_bump=0.08,
        cooldown_minutes=45,
    )
    r.note_utterance(class_="memory_magic")
    c.advance(seconds=30)
    r.note_acknowledgment()
    c.advance(seconds=60)
    r.tick()
    assert r.is_active() is False


def test_cooldown_expires():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    r = SocialRecovery(
        clock=c,
        timeout_seconds=60,
        confidence_bump=0.08,
        cooldown_minutes=45,
    )
    r.note_utterance(class_="memory_magic")
    c.advance(seconds=61)
    r.tick()
    assert r.is_active() is True
    c.advance(seconds=45 * 60 + 1)
    r.tick()
    assert r.is_active() is False
    assert r.threshold_bump() == 0.0
