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
