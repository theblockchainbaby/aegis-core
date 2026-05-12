"""Forbidden-tone classifier — rule-based regex gate.

Plan D ships this regex-based version. Plan E or post-90-day-dogfood
replaces it with a small distilled local classifier fine-tuned on the
intervention log. Interface stays the same.

Patterns per spec §6 forbidden_tones list. Conservative on purpose — false
positives are cheaper than false negatives (the whole point of the gate).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Each tone maps to a list of regex patterns (compiled at module load).
_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "imperative": [
        re.compile(r"\byou\s+should\b", re.IGNORECASE),
        re.compile(r"\byou\s+need\s+to\b", re.IGNORECASE),
        re.compile(r"\byou\s+must\b", re.IGNORECASE),
        re.compile(r"\b(?:try|take|do|start|stop)\s+(?:to|a|an|some)\b", re.IGNORECASE),
        re.compile(r"^\s*(?:try|take|do|start|stop)\b", re.IGNORECASE),
    ],
    "exclamation": [
        re.compile(r"!"),
        re.compile(r"\b(?:congrats|congratulations|nice|awesome|amazing)\b", re.IGNORECASE),
    ],
    "coaching": [
        re.compile(r"\bgreat\s+(?:job|work)\b", re.IGNORECASE),
        re.compile(r"\bkeep\s+it\s+up\b", re.IGNORECASE),
        re.compile(r"\blet'?s\b", re.IGNORECASE),
        re.compile(r"\byou'?re\s+doing\b", re.IGNORECASE),
        re.compile(r"\bproud\s+of\s+you\b", re.IGNORECASE),
    ],
    "quantified_advice": [
        re.compile(r"\bfor\s+\d+\s+(?:seconds|minutes|hours|times)\b", re.IGNORECASE),
        re.compile(r"\b\d+\s+times\s+(?:more|less|a\s+day|per\s+day)\b", re.IGNORECASE),
    ],
    "hedging_assistantese": [
        re.compile(r"\bjust\s+wanted\s+to\b", re.IGNORECASE),
        re.compile(r"\bif\s+you'?d\s+like\b", re.IGNORECASE),
        re.compile(r"\bhappy\s+to\b", re.IGNORECASE),
        re.compile(r"\bi'?m\s+here\s+to\b", re.IGNORECASE),
    ],
}


@dataclass(frozen=True)
class ToneVerdict:
    passes: bool
    forbidden_tones: list[str]


class ToneClassifier:
    def __init__(self, active_tones: list[str] | None = None) -> None:
        self._active = (
            list(active_tones)
            if active_tones is not None
            else list(_PATTERNS)
        )

    def evaluate(self, text: str) -> ToneVerdict:
        hits: list[str] = []
        for tone in self._active:
            patterns = _PATTERNS.get(tone, [])
            for p in patterns:
                if p.search(text):
                    hits.append(tone)
                    break
        return ToneVerdict(passes=(not hits), forbidden_tones=hits)
