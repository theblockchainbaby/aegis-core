from aegis_core.services.mind.redaction import redact_for_cloud


def test_passes_through_safe_fields():
    raw = {
        "moment_summary": "Long focused session on the landing page redesign.",
        "themes": ["landing", "redesign"],
        "intervention_class": "memory_magic",
        "confidence": 0.88,
    }
    out = redact_for_cloud(raw)
    assert out["moment_summary"] == raw["moment_summary"]
    assert out["themes"] == raw["themes"]


def test_strips_raw_audio_frames_pii_keys():
    raw = {
        "moment_summary": "ok",
        "audio_bytes": b"raw audio data",
        "camera_frame": b"jpeg bytes",
        "user_email": "york@example.com",
        "user_phone": "+1-555-1234",
        "pii_full_name": "York Sims",
    }
    out = redact_for_cloud(raw)
    assert "audio_bytes" not in out
    assert "camera_frame" not in out
    assert "user_email" not in out
    assert "user_phone" not in out
    assert "pii_full_name" not in out
    assert out["moment_summary"] == "ok"


def test_strips_nested_bytes():
    raw = {
        "moment_summary": "ok",
        "nested": {
            "audio": b"raw",
            "themes": ["safe"],
        },
    }
    out = redact_for_cloud(raw)
    assert "audio" not in out["nested"]
    assert out["nested"]["themes"] == ["safe"]


def test_redaction_is_a_copy_not_mutation():
    raw = {"audio_bytes": b"x", "summary": "ok"}
    out = redact_for_cloud(raw)
    assert "audio_bytes" in raw  # original untouched
    assert "audio_bytes" not in out
