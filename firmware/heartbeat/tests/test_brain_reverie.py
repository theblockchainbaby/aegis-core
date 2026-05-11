import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain_reverie import ReverieMonitor, REVERIE_TIMEOUT_MS


def test_no_reverie_when_frames_recent():
    m = ReverieMonitor()
    m.note_frame()
    assert m.check() is None
    assert m.in_reverie is False


def test_reverie_enters_after_timeout(monkeypatch):
    import brain_reverie

    fake_now = [0]

    class FakeTime:
        @staticmethod
        def ticks_ms():
            return fake_now[0]

        @staticmethod
        def ticks_diff(a, b):
            return a - b

    monkeypatch.setattr(brain_reverie, "time", FakeTime)

    m = ReverieMonitor()
    m.note_frame()
    fake_now[0] += REVERIE_TIMEOUT_MS + 1
    assert m.check() == "enter"
    assert m.in_reverie is True


def test_reverie_exits_on_next_frame(monkeypatch):
    import brain_reverie

    fake_now = [0]

    class FakeTime:
        @staticmethod
        def ticks_ms():
            return fake_now[0]

        @staticmethod
        def ticks_diff(a, b):
            return a - b

    monkeypatch.setattr(brain_reverie, "time", FakeTime)

    m = ReverieMonitor()
    m.note_frame()
    fake_now[0] += REVERIE_TIMEOUT_MS + 1
    assert m.check() == "enter"
    m.note_frame()
    assert m.check() == "exit"
    assert m.in_reverie is False
