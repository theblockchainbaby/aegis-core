"""steward service — the gatekeeper.

Plan D Task 9 (skeleton): subscribes to mind.utterance_proposal and
state.changed; runs the gate; logs the decision to InterventionStore. No
voice.speak publication yet — Task 10 wires that. Social recovery and
scar tissue are added in Tasks 11 + 12.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import (
    InterventionClass,
    PresenceState,
    StateChanged,
    UtteranceProposal,
)
from ...storage._conn import connect
from ...storage.interventions import InterventionStore
from ...storage.scar_tissue import ScarTissueStore
from ...storage.schema import run_migrations
from .._base import AegisService
from .attention import AttentionSignals, StubAttentionSignals
from .clock import Clock, SystemClock
from .gate import GateState, evaluate
from .rules import Rules, load_rules
from .tone_classifier import ToneClassifier

log = structlog.get_logger()

DEFAULT_DB_PATH = "/tmp/aegis-memory.db"


class StewardService(AegisService):
    name = "steward"

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        rules_path: str | Path | None = None,
        signals: AttentionSignals | None = None,
        clock: Clock | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path)
        self._rules_path = (
            Path(rules_path)
            if rules_path is not None
            else Path(__file__).resolve().parents[4] / "rules" / "intervention.yaml"
        )
        self._signals: AttentionSignals = signals or StubAttentionSignals()
        self._clock: Clock = clock or SystemClock()

        # State that the gate consults:
        self._presence_state: PresenceState = PresenceState.DORMANT
        self._silence_budget_remaining: float = 0.0
        self._utterances_today: int = 0
        self._last_utterance_at: datetime | None = None

        # Resources opened in setup():
        self._conn = None
        self._interventions: InterventionStore | None = None
        self._scar: ScarTissueStore | None = None
        self._rules: Rules | None = None
        self._tone: ToneClassifier | None = None
        self._bus: AegisBus | None = None
        self._last_aired_id: int | None = None
        self._last_aired_class: str | None = None

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        # Load rules at startup.
        self._rules = load_rules(self._rules_path)
        self._tone = ToneClassifier()
        self._silence_budget_remaining = self._rules.silence_budget.default_weight_per_day

        # Open DB.
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._interventions = InterventionStore(self._conn)
        self._scar = ScarTissueStore(self._conn)

        await bus.subscribe("state.changed", StateChanged, self._on_state)
        await bus.subscribe(
            "mind.utterance_proposal", UtteranceProposal, self._on_proposal
        )

    async def teardown(self, bus: AegisBus) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

    async def _on_state(self, msg: StateChanged) -> None:
        self._presence_state = msg.current

    async def _on_proposal(self, msg: UtteranceProposal) -> None:
        if (
            self._interventions is None
            or self._rules is None
            or self._tone is None
            or self._scar is None
        ):
            return

        gate_state = GateState(
            presence_state=self._presence_state,
            silence_budget_remaining=self._silence_budget_remaining,
            utterances_today=self._utterances_today,
            last_utterance_at=self._last_utterance_at,
            presence_decay_multiplier=1.0,
            scar_tissue_penalty=self._scar.get_penalty(
                str(msg.intervention_class)
            ),
            recovery_threshold_bump=0.0,
        )
        decision = evaluate(
            msg,
            gate_state,
            rules=self._rules,
            tone=self._tone,
            signals=self._signals,
            clock=self._clock,
        )

        now = self._clock.now()
        if decision.proceed:
            self._last_aired_id = self._interventions.log_aired(
                timestamp=now,
                intervention_class=str(msg.intervention_class),
                weight=msg.weight,
                confidence=msg.confidence,
                text=msg.text,
            )
            self._last_aired_class = str(msg.intervention_class)
            if self._bus is not None:
                from ...messages import VoiceSpeak

                await self._bus.publish(
                    "voice.speak",
                    VoiceSpeak(
                        timestamp=now,
                        text=msg.text,
                        intervention_class=msg.intervention_class,
                        weight=msg.weight,
                    ),
                )
            self._silence_budget_remaining -= decision.weight_cost
            self._utterances_today += 1
            self._last_utterance_at = now
        else:
            self._interventions.log_vetoed(
                timestamp=now,
                intervention_class=str(msg.intervention_class),
                weight=msg.weight,
                confidence=msg.confidence,
                text=msg.text,
                reasons=decision.reasons,
            )


def make_service(**kwargs) -> StewardService:
    return StewardService(**kwargs)
