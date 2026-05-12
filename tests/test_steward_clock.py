from datetime import UTC, datetime, timedelta

from aegis_core.services.steward.clock import Clock, FakeClock, SystemClock


def test_system_clock_returns_utc_now():
    c = SystemClock()
    now = c.now()
    assert now.tzinfo is not None
    # Within a couple seconds of wall now.
    assert abs((datetime.now(UTC) - now).total_seconds()) < 2.0


def test_fake_clock_starts_at_specified_time():
    start = datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC)
    c = FakeClock(start)
    assert c.now() == start


def test_fake_clock_advance():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    c.advance(seconds=120)
    assert c.now() == datetime(2026, 5, 12, 9, 2, 0, tzinfo=UTC)


def test_fake_clock_monotonic_increases():
    c = FakeClock(datetime(2026, 5, 12, 9, 0, 0, tzinfo=UTC))
    t0 = c.monotonic()
    c.advance(seconds=5)
    t1 = c.monotonic()
    assert t1 == t0 + 5.0


def test_clock_protocol_satisfied_by_both():
    sys = SystemClock()
    fake = FakeClock(datetime.now(UTC))
    assert isinstance(sys, Clock)
    assert isinstance(fake, Clock)
