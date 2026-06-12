"""steward service — the gatekeeper.

Plan D Task 9 (skeleton): subscribes to mind.utterance_proposal and
state.changed; runs the gate; logs the decision to InterventionStore. No
voice.speak publication yet — Task 10 wires that. Social recovery and
scar tissue are added in Tasks 11 + 12.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import structlog

from ...bus import AegisBus
from ...messages import (
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
from .decay import PresenceDecay
from .gate import GateState, evaluate
from .recovery import SocialRecovery
from .rules import Rules, load_rules
from .tone_classifier import ToneClassifier

log = structlog.get_logger()

DEFAULT_DB_PATH = str(Path.home() / ".aegis-core" / "memory.db")


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
        self._recovery: SocialRecovery | None = None
        self._recovery_tick_task = None
        self._decay: PresenceDecay | None = None
        self._acks_this_window = 0

    async def setup(self, bus: AegisBus) -> None:
        self._bus = bus
        # Load rules at startup.
        self._rules = load_rules(self._rules_path)
        self._tone = ToneClassifier()
        self._silence_budget_remaining = self._rules.silence_budget.default_weight_per_day
        self._recovery = SocialRecovery(
            clock=self._clock,
            timeout_seconds=self._rules.social_recovery.trigger.utterance_unacknowledged_for_seconds,
            confidence_bump=self._rules.social_recovery.effects.confidence_threshold_bump,
            cooldown_minutes=self._rules.social_recovery.effects.cooldown_duration_minutes,
        )

        self._decay = PresenceDecay(
            clock=self._clock,
            window_days=self._rules.presence_decay.measurement_window_days,
            low_engagement_threshold_per_week=self._rules.presence_decay.low_engagement_threshold_per_week,
            multiplier_per_step=self._rules.confidence_threshold.presence_decay_multiplier_per_week,
            floor=self._rules.presence_decay.floor.silence_budget_min,
            baseline_budget=self._rules.silence_budget.default_weight_per_day,
        )

        # Open DB.
        self._conn = connect(self._db_path)
        run_migrations(self._conn)
        self._interventions = InterventionStore(self._conn)
        self._scar = ScarTissueStore(self._conn)

        await bus.subscribe("state.changed", StateChanged, self._on_state)
        await bus.subscribe(
            "mind.utterance_proposal", UtteranceProposal, self._on_proposal
        )

        import asyncio as _asyncio

        self._recovery_tick_task = _asyncio.create_task(self._recovery_tick_loop())

    async def teardown(self, bus: AegisBus) -> None:
        if self._recovery_tick_task is not None:
            self._recovery_tick_task.cancel()
            try:
                await self._recovery_tick_task
            except BaseException:
                pass
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

    async def _on_state(self, msg: StateChanged) -> None:
        prev_state = self._presence_state
        self._presence_state = msg.current

        # If we just left Reflective into Settling and we have a recent aired
        # utterance, treat as acknowledged. Plan D approximation; Plan E adds
        # real voice/response detection.
        if (
            prev_state == PresenceState.REFLECTIVE
            and msg.current == PresenceState.SETTLING
            and self._last_aired_class is not None
            and self._recovery is not None
            and self._scar is not None
            and self._rules is not None
        ):
            self._scar.recover(
                self._last_aired_class,
                by=self._rules.conversational_scar_tissue.recovery_on_acknowledgment,
                floor=self._rules.conversational_scar_tissue.floor,
            )
            self._recovery.note_acknowledgment()
            if self._last_aired_id is not None and self._interventions is not None:
                self._interventions.mark_acknowledged(
                    self._last_aired_id,
                    acknowledged=True,
                    at=self._clock.now(),
                )
            self._last_aired_id = None
            self._last_aired_class = None
            self._acks_this_window += 1

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
            presence_decay_multiplier=(
                self._decay.multiplier() if self._decay is not None else 1.0
            ),
            scar_tissue_penalty=self._scar.get_penalty(
                str(msg.intervention_class)
            ),
            recovery_threshold_bump=(
                self._recovery.threshold_bump() if self._recovery is not None else 0.0
            ),
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
            if self._recovery is not None:
                self._recovery.note_utterance(class_=str(msg.intervention_class))
        else:
            self._interventions.log_vetoed(
                timestamp=now,
                intervention_class=str(msg.intervention_class),
                weight=msg.weight,
                confidence=msg.confidence,
                text=msg.text,
                reasons=decision.reasons,
            )
            # Scar tissue: this class repeatedly fails the gate → raise the
            # bar for future proposals in this class.
            self._scar.bump_veto(
                str(msg.intervention_class),
                by=self._rules.conversational_scar_tissue.vetoed_repeat_penalty,
                cap=self._rules.conversational_scar_tissue.cap,
            )

    async def _recovery_tick_loop(self) -> None:
        import asyncio as _asyncio

        counter = 0
        while not self._shutdown.is_set():
            await _asyncio.sleep(5)
            if self._recovery is not None:
                self._recovery.tick()
            counter += 1
            if counter >= 12 and self._decay is not None:  # ~every minute
                counter = 0
                self._decay.tick(acknowledged_this_window=self._acks_this_window)
                self._acks_this_window = 0


def make_service(**kwargs) -> StewardService:
    return StewardService(**kwargs)
