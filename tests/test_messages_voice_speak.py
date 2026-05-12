from datetime import UTC, datetime

from aegis_core.messages import InterventionClass, VoiceSpeak


def test_voice_speak_roundtrip():
    msg = VoiceSpeak(
        timestamp=datetime.now(UTC),
        text="You usually stop around now.",
        voice_persona="desk_companion",
        intervention_class=InterventionClass.ROUTINE_CONTINUITY,
        weight=0.5,
    )
    assert VoiceSpeak.model_validate_json(msg.model_dump_json()) == msg


def test_voice_speak_default_persona():
    msg = VoiceSpeak(
        timestamp=datetime.now(UTC),
        text="x",
        intervention_class=InterventionClass.AMBIENT_NOTE,
        weight=0.1,
    )
    assert msg.voice_persona == "desk_companion"
