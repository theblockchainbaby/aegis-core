from aegis_core.services.steward.attention import (
    AttentionSignals,
    ProgrammableAttentionSignals,
    StubAttentionSignals,
)


def test_stub_signals_default_no_competition():
    s = StubAttentionSignals()
    assert s.is_typing() is False
    assert s.is_in_call() is False
    assert s.is_video_playing() is False
    assert s.seconds_since_last_pause() >= 10.0


def test_programmable_signals_set_states():
    s = ProgrammableAttentionSignals()
    s.set_typing(True)
    s.set_in_call(True)
    s.set_video_playing(True)
    s.set_seconds_since_last_pause(0.5)
    assert s.is_typing() is True
    assert s.is_in_call() is True
    assert s.is_video_playing() is True
    assert s.seconds_since_last_pause() == 0.5


def test_signal_classes_implement_protocol():
    assert isinstance(StubAttentionSignals(), AttentionSignals)
    assert isinstance(ProgrammableAttentionSignals(), AttentionSignals)
