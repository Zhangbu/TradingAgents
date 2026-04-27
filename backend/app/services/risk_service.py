from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.analysis import PlatformMode
from backend.app.schemas.trade_intent import (
    RiskCheck,
    RiskOutcome,
    RiskSeverity,
    RiskSummary,
    TradeIntentRecord,
    TradeIntentStatus,
    TradeSide,
)


class RiskService:
    """Applies deterministic Phase 2 risk rules to structured trade intents."""

    def evaluate(self, intent: TradeIntentRecord) -> TradeIntentRecord:
        checks: list[RiskCheck] = []

        self._check_actionable_signal(intent, checks)
        self._check_position_size(intent, checks)
        self._check_confidence(intent, checks)
        self._check_risk_controls(intent, checks)
        self._check_mode_constraints(intent, checks)
        self._check_flags(intent, checks)

        outcome = self._derive_status(checks)
        intent.risk_summary = RiskSummary(outcome=outcome, checks=checks)
        intent.status = outcome
        intent.updated_at = datetime.now(timezone.utc)
        return intent

    def _check_actionable_signal(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if intent.side == TradeSide.hold:
            checks.append(
                RiskCheck(
                    rule_code="signal.hold_not_actionable",
                    severity=RiskSeverity.warning,
                    outcome=RiskOutcome.block,
                    message="Hold signals are stored for review but cannot become executable orders.",
                )
            )
        else:
            checks.append(
                RiskCheck(
                    rule_code="signal.actionable",
                    severity=RiskSeverity.info,
                    outcome=RiskOutcome.pass_check,
                    message="Signal side is actionable for downstream order construction.",
                )
            )

    def _check_position_size(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if intent.max_position_pct > 0.10:
            checks.append(
                RiskCheck(
                    rule_code="sizing.max_position_pct",
                    severity=RiskSeverity.critical,
                    outcome=RiskOutcome.block,
                    message="Maximum position size exceeds the Phase 2 hard cap of 10%.",
                )
            )
            return

        checks.append(
            RiskCheck(
                rule_code="sizing.max_position_pct",
                severity=RiskSeverity.info,
                outcome=RiskOutcome.pass_check,
                message="Maximum position size is within the Phase 2 hard cap.",
            )
        )

    def _check_confidence(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if intent.side != TradeSide.hold and intent.confidence < 0.60:
            checks.append(
                RiskCheck(
                    rule_code="signal.min_confidence",
                    severity=RiskSeverity.critical,
                    outcome=RiskOutcome.block,
                    message="Actionable signals must have confidence of at least 0.60.",
                )
            )
            return

        checks.append(
            RiskCheck(
                rule_code="signal.min_confidence",
                severity=RiskSeverity.info,
                outcome=RiskOutcome.pass_check,
                message="Signal confidence satisfies the minimum Phase 2 threshold.",
            )
        )

    def _check_risk_controls(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if intent.side != TradeSide.hold and intent.max_loss_pct <= 0:
            checks.append(
                RiskCheck(
                    rule_code="risk.max_loss_pct",
                    severity=RiskSeverity.critical,
                    outcome=RiskOutcome.block,
                    message="Executable signals require a positive maximum loss threshold.",
                )
            )
            return

        checks.append(
            RiskCheck(
                rule_code="risk.max_loss_pct",
                severity=RiskSeverity.info,
                outcome=RiskOutcome.pass_check,
                message="A maximum loss threshold is present for the signal.",
            )
        )

    def _check_mode_constraints(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if intent.mode == PlatformMode.analysis_only:
            checks.append(
                RiskCheck(
                    rule_code="mode.analysis_only",
                    severity=RiskSeverity.warning,
                    outcome=RiskOutcome.block,
                    message="Analysis-only mode forbids order creation.",
                )
            )
        elif intent.mode == PlatformMode.live_auto:
            checks.append(
                RiskCheck(
                    rule_code="mode.live_auto_disabled",
                    severity=RiskSeverity.critical,
                    outcome=RiskOutcome.block,
                    message="Live auto execution remains disabled in Phase 2.",
                )
            )
        elif intent.mode in {PlatformMode.paper_manual, PlatformMode.live_manual}:
            checks.append(
                RiskCheck(
                    rule_code="mode.manual_approval",
                    severity=RiskSeverity.warning,
                    outcome=RiskOutcome.require_approval,
                    message="Manual modes require operator approval before order submission.",
                )
            )
        else:
            checks.append(
                RiskCheck(
                    rule_code="mode.paper_auto",
                    severity=RiskSeverity.info,
                    outcome=RiskOutcome.pass_check,
                    message="Paper auto mode is eligible for automated execution after risk checks pass.",
                )
            )

    def _check_flags(self, intent: TradeIntentRecord, checks: list[RiskCheck]) -> None:
        if not intent.risk_flags:
            checks.append(
                RiskCheck(
                    rule_code="flags.none",
                    severity=RiskSeverity.info,
                    outcome=RiskOutcome.pass_check,
                    message="No elevated narrative risk flags were detected in the thesis.",
                )
            )
            return

        if any(flag in {"earnings_risk", "regulatory_risk", "high_volatility"} for flag in intent.risk_flags):
            checks.append(
                RiskCheck(
                    rule_code="flags.elevated_event_risk",
                    severity=RiskSeverity.warning,
                    outcome=RiskOutcome.require_approval,
                    message="Elevated narrative risk flags require manual review before execution.",
                )
            )
        else:
            checks.append(
                RiskCheck(
                    rule_code="flags.observed",
                    severity=RiskSeverity.warning,
                    outcome=RiskOutcome.require_approval,
                    message="Narrative risk flags were detected and should be reviewed by an operator.",
                )
            )

    def _derive_status(self, checks: list[RiskCheck]) -> TradeIntentStatus:
        if any(check.outcome == RiskOutcome.block for check in checks):
            return TradeIntentStatus.blocked
        if any(check.outcome == RiskOutcome.require_approval for check in checks):
            return TradeIntentStatus.approval_required
        return TradeIntentStatus.ready
