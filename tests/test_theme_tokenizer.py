from aegis_core.services.keeper.theme_tokenizer import tokenize_themes


def test_tokenize_filters_stopwords():
    keys = tokenize_themes("The user mentioned the landing page redesign before lunch")
    assert "landing" in keys
    assert "page" in keys
    assert "redesign" in keys
    assert "lunch" in keys
    # Stopwords excluded.
    assert "the" not in keys
    assert "before" not in keys


def test_tokenize_returns_unique_lowercased():
    # Note: Uses 'Refactor' instead of 'Focus' because 'focus' is in STOPWORDS
    # by design (every focus_session Moment mentions it; we don't want it to
    # dominate themes). This test probe uses a non-stopword to verify deduplication
    # and lowercasing, preserving the test's intent.
    keys = tokenize_themes("Refactor Refactor REFACTOR work work")
    assert keys.count("refactor") == 1
    assert keys.count("work") == 1


def test_tokenize_handles_empty():
    assert tokenize_themes("") == []
    assert tokenize_themes(None) == []
