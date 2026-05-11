"""Hardware Privacy State — MCU-enforced contract.

The MCU honors this mapping regardless of what the Jetson tells it. The mic
power rail is gated by `mic_should_be_powered(state)` — even if a malicious
or buggy Jetson tries to enable the mic in Dormant, the MCU vetoes.
"""

STATE_ORDINALS = {
    "sleep": 0,
    "dormant": 1,
    "observing": 2,
    "attentive": 3,
    "settling": 4,
    "reflective": 5,
    "quiet": 6,
}

# Inverse map for ordinal → name lookups.
STATE_NAMES = {v: k for k, v in STATE_ORDINALS.items()}


def mic_should_be_powered(state: str) -> bool:
    """Hardware-enforced: mic rail off in Sleep + Dormant."""
    return state not in ("sleep", "dormant")


def palette_name_for_state(state: str) -> str:
    """Identity mapping — palette names match state names in v1."""
    return state


def state_from_ordinal(ordinal: int) -> str:
    return STATE_NAMES.get(ordinal, "dormant")  # safe default
