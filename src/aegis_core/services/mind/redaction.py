"""Redaction layer — strip cloud-unsafe fields before any cognition escalation.

Plan E ships the conservative version: drop bytes values, drop any key
that starts with 'pii_' or matches common-PII prefixes (email/phone/etc.),
and recurse into nested dicts. Plan E' tightens further if needed.

The layer is a pure function. It does not redact text content itself — the
calling code's responsibility is to NOT put raw text it doesn't want in
the context dict in the first place. Memory summaries are user-volunteered
by definition.
"""
from __future__ import annotations

from typing import Any

_PII_KEY_PATTERNS = (
    "audio",
    "camera",
    "frame",
    "user_email",
    "user_phone",
    "pii_",
    "raw_",
)


def _is_pii_key(key: str) -> bool:
    k = key.lower()
    return any(p in k for p in _PII_KEY_PATTERNS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return None  # sentinel — caller filters None values
    if isinstance(value, dict):
        return _redact_dict(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value if not isinstance(v, bytes)]
    return value


def _redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if _is_pii_key(k):
            continue
        rv = _redact_value(v)
        if rv is None and isinstance(v, bytes):
            continue
        out[k] = rv
    return out


def redact_for_cloud(context: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `context` safe to send to a cloud LLM."""
    return _redact_dict(context)
