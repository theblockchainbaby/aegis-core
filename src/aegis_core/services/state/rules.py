"""Presence State Machine rules — transition table + dwell minimums.

Pure data. The machine module imports and consults this; no I/O.
"""
from ...messages import PresenceState

# Minimum dwell in each state before any transition is allowed.
# Compressed for tests; production values per spec §5 live in a separate
# config or override in service.py later.
MIN_DWELL_MS: dict[PresenceState, int] = {
    PresenceState.SLEEP: 6_000,
    PresenceState.DORMANT: 1_000,
    PresenceState.OBSERVING: 500,
    PresenceState.ATTENTIVE: 1_000,
    PresenceState.SETTLING: 500,
    PresenceState.REFLECTIVE: 300,
    PresenceState.QUIET: 2_000,
}

# Allowed direct transitions. Anything not listed must go through Settling
# (handled in machine.py). Reflective is special-cased: enter direct from
# Attentive; leave must pass through Settling.
ALLOWED_DIRECT: dict[PresenceState, set[PresenceState]] = {
    PresenceState.SLEEP: {PresenceState.DORMANT},
    PresenceState.DORMANT: {PresenceState.OBSERVING, PresenceState.SLEEP},
    PresenceState.OBSERVING: {PresenceState.ATTENTIVE, PresenceState.DORMANT, PresenceState.QUIET},
    PresenceState.ATTENTIVE: {PresenceState.REFLECTIVE, PresenceState.SETTLING},
    PresenceState.SETTLING: {PresenceState.ATTENTIVE, PresenceState.OBSERVING},
    PresenceState.REFLECTIVE: {PresenceState.SETTLING},  # leaving must Settle
    PresenceState.QUIET: {PresenceState.OBSERVING},
}


def is_allowed(from_state: PresenceState, to_state: PresenceState) -> bool:
    return to_state in ALLOWED_DIRECT.get(from_state, set())
