"""Theme tokenizer — pure function from Moment summary → theme keys.

Plan C uses a small stopword-filtered word splitter. Plan E replaces this
with embedding-derived theme clustering when `mind` retrieves them.
"""
from __future__ import annotations

import re

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "but", "by",
    "for", "from", "had", "has", "have", "he", "her", "his", "in", "is",
    "it", "its", "of", "on", "or", "she", "that", "the", "their", "they",
    "this", "to", "user", "was", "with", "you", "your",
    # plus common Plan C signature words that aren't themes
    "events", "focus", "voice",
    "posture", "score", "minutes", "seconds", "hours",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]+")


def tokenize_themes(text: str | None) -> list[str]:
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _WORD_RE.finditer(text):
        word = m.group(0).lower()
        if word in STOPWORDS:
            continue
        if word in seen:
            continue
        seen.add(word)
        out.append(word)
    return out
