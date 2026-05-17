import sys

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_read_idle_seconds_returns_non_negative_float():
    from aegis_core.services.senses.sources.host_activity import (
        read_idle_seconds,
    )

    value = read_idle_seconds()
    assert isinstance(value, float)
    assert value >= 0.0


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_read_frontmost_app_returns_str_or_none():
    from aegis_core.services.senses.sources.host_activity import (
        read_frontmost_app,
    )

    value = read_frontmost_app()
    assert value is None or isinstance(value, str)


@pytest.mark.asyncio
async def test_source_yields_presence_and_posture_per_poll():
    from aegis_core.services.senses.sources.host_activity import (
        HostActivitySource,
    )
    from aegis_core.services.senses.sources.host_activity_reader import (
        ActivityThresholds,
    )

    source = HostActivitySource(
        poll_interval_seconds=0.01,
        thresholds=ActivityThresholds(),
        idle_reader=lambda: 5.0,
        app_reader=lambda: "Code",
    )

    collected = []
    async for subject, msg in source.events():
        collected.append((subject, msg))
        if len(collected) == 4:
            await source.aclose()
            break

    subjects = [subject for subject, _ in collected]
    assert subjects == [
        "senses.presence",
        "senses.posture",
        "senses.presence",
        "senses.posture",
    ]
    assert collected[0][1].present is True
    assert collected[0][1].source == "host_input"
    assert collected[1][1].gaze == "screen"
