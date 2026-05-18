from datetime import UTC, datetime
from pathlib import Path

from aegis_core.services.observer.scheduler import (
    ScheduleConfig,
    Scheduler,
    load_schedule,
)

REPO_SCHEDULE = (
    Path(__file__).resolve().parent.parent / "rules" / "schedule.yaml"
)


def test_load_schedule_from_yaml():
    cfg = load_schedule(REPO_SCHEDULE)
    assert cfg.morning_reflection == "09:00"
    assert cfg.quiet_hours_start == "22:00"


def test_scheduler_fires_morning_at_configured_time():
    cfg = ScheduleConfig(
        morning_reflection="09:00",
        evening_reflection="18:00",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    s = Scheduler(cfg)
    triggers = s.tick(now=datetime(2026, 5, 12, 9, 0, 30, tzinfo=UTC))
    names = [t.name for t in triggers]
    assert "morning_reflection" in names


def test_scheduler_does_not_double_fire_within_same_window():
    cfg = ScheduleConfig(
        morning_reflection="09:00",
        evening_reflection="18:00",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    s = Scheduler(cfg)
    s.tick(now=datetime(2026, 5, 12, 9, 0, 30, tzinfo=UTC))
    triggers = s.tick(now=datetime(2026, 5, 12, 9, 0, 45, tzinfo=UTC))
    names = [t.name for t in triggers]
    assert "morning_reflection" not in names


def test_scheduler_fires_morning_on_new_day():
    cfg = ScheduleConfig(
        morning_reflection="09:00",
        evening_reflection="18:00",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    s = Scheduler(cfg)
    s.tick(now=datetime(2026, 5, 12, 9, 0, 30, tzinfo=UTC))
    triggers = s.tick(now=datetime(2026, 5, 13, 9, 0, 30, tzinfo=UTC))
    names = [t.name for t in triggers]
    assert "morning_reflection" in names


def test_scheduler_fires_quiet_hours_both_ends():
    cfg = ScheduleConfig(
        morning_reflection="09:00",
        evening_reflection="18:00",
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
    )
    s = Scheduler(cfg)
    starts = s.tick(now=datetime(2026, 5, 12, 22, 0, 5, tzinfo=UTC))
    ends = s.tick(now=datetime(2026, 5, 13, 7, 0, 5, tzinfo=UTC))
    assert any(t.name == "quiet_hours_start" for t in starts)
    assert any(t.name == "quiet_hours_end" for t in ends)
