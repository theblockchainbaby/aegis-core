"""Scheduler — fires synthetic state.changed events at configured times.

TEMPORARY (Plan F): this is the placeholder scheduler. It exists so the
operator can give the system a coarse daily rhythm (morning reflection,
evening reflection, quiet hours) while we dogfood. Future plans will
replace this with richer logic (calendar-aware, fatigue-aware,
mood-aware). Do not generalize it further now.

Pure logic: tick(now) returns the list of ScheduledTriggers that should
fire at that wall-clock instant, given the configured schedule and the
last-fired tracker (which is internal to the Scheduler instance).

The observer service ticks every 30 seconds and publishes one
state.changed per trigger. Same publish-events-not-state-mutation
pattern as the trace replay tool: every cause is observable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class ScheduleConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    morning_reflection: str
    evening_reflection: str
    quiet_hours_start: str
    quiet_hours_end: str


def load_schedule(path: str | Path) -> ScheduleConfig:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"schedule file {path} did not parse to a mapping")
    return ScheduleConfig.model_validate(raw)


@dataclass(frozen=True)
class ScheduledTrigger:
    name: str
    target_state: str  # 'reflective' / 'sleep' / 'dormant'
    reason: str


_TRIGGERS: dict[str, tuple[str, str]] = {
    "morning_reflection": ("reflective", "scheduled_morning"),
    "evening_reflection": ("reflective", "scheduled_evening"),
    "quiet_hours_start": ("sleep", "scheduled_quiet"),
    "quiet_hours_end": ("dormant", "scheduled_wake"),
}


def _parse_hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


class Scheduler:
    def __init__(self, config: ScheduleConfig) -> None:
        self._config = config
        self._fired: set[tuple[date, str]] = set()

    def tick(self, now: datetime) -> list[ScheduledTrigger]:
        out: list[ScheduledTrigger] = []
        local_today = now.date()

        windows = {
            "morning_reflection": _parse_hm(self._config.morning_reflection),
            "evening_reflection": _parse_hm(self._config.evening_reflection),
            "quiet_hours_start": _parse_hm(self._config.quiet_hours_start),
            "quiet_hours_end": _parse_hm(self._config.quiet_hours_end),
        }

        for name, t in windows.items():
            target_state, reason = _TRIGGERS[name]
            scheduled_dt = datetime.combine(local_today, t, tzinfo=now.tzinfo)
            delta = (now - scheduled_dt).total_seconds()
            key = (local_today, name)
            if 0 <= delta <= 60 and key not in self._fired:
                self._fired.add(key)
                out.append(
                    ScheduledTrigger(
                        name=name,
                        target_state=target_state,
                        reason=reason,
                    )
                )
        return out
