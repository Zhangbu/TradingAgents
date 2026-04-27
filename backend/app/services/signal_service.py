from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.app.schemas.analysis import AnalysisRunRecord
from backend.app.schemas.trade_intent import (
    EntryType,
    TimeHorizon,
    TradeIntentRecord,
    TradeIntentStatus,
    TradeRating,
    TradeSide,
)


class SignalService:
    """Builds a deterministic structured trade intent from an analysis run."""

    _RATING_MAP = {
        "BUY": (TradeRating.buy, TradeSide.buy, 0.78, 0.08),
        "OVERWEIGHT": (TradeRating.overweight, TradeSide.buy, 0.68, 0.05),
        "HOLD": (TradeRating.hold, TradeSide.hold, 0.55, 0.0),
        "UNDERWEIGHT": (TradeRating.underweight, TradeSide.sell, 0.66, 0.05),
        "SELL": (TradeRating.sell, TradeSide.sell, 0.8, 0.08),
    }

    _FLAG_PATTERNS = {
        "earnings_risk": re.compile(r"\bearnings?\b", re.IGNORECASE),
        "high_volatility": re.compile(r"\bvolatil\w+\b", re.IGNORECASE),
        "macro_risk": re.compile(r"\bmacro|rates?|inflation|fed\b", re.IGNORECASE),
        "regulatory_risk": re.compile(r"\bregulat\w+|antitrust|lawsuit\b", re.IGNORECASE),
        "low_confidence_language": re.compile(r"\buncertain|mixed|unclear|ambiguous\b", re.IGNORECASE),
    }

    def build_from_analysis(self, record: AnalysisRunRecord) -> TradeIntentRecord:
        if record.artifacts is None:
            raise ValueError("Analysis run has no artifacts to convert into a trade intent.")

        normalized_signal = (record.artifacts.processed_signal or "HOLD").strip().upper()
        rating, side, confidence, max_position_pct = self._RATING_MAP.get(
            normalized_signal,
            self._RATING_MAP["HOLD"],
        )

        final_decision = (record.artifacts.final_trade_decision or "").strip()
        thesis_summary = self._summarize(final_decision)
        risk_flags = self._extract_flags(final_decision)

        entry_type = EntryType.none if side == TradeSide.hold else EntryType.market
        max_loss_pct = 0.0 if side == TradeSide.hold else 0.03
        take_profit_pct = 0.0 if side == TradeSide.hold else 0.09

        if "low_confidence_language" in risk_flags:
            confidence = min(confidence, 0.58)

        return TradeIntentRecord(
            analysis_id=record.id,
            symbol=record.symbol,
            trade_date=record.trade_date,
            mode=record.mode,
            rating=rating,
            side=side,
            status=TradeIntentStatus.draft,
            confidence=confidence,
            entry_type=entry_type,
            time_horizon=TimeHorizon.swing,
            max_position_pct=max_position_pct,
            max_loss_pct=max_loss_pct,
            take_profit_pct=take_profit_pct,
            thesis_summary=thesis_summary,
            source_signal=normalized_signal,
            risk_flags=risk_flags,
            updated_at=datetime.now(timezone.utc),
        )

    def _summarize(self, text: str) -> str:
        if not text:
            return "No detailed thesis was returned by the analysis layer."

        clean = " ".join(text.split())
        return clean[:280]

    def _extract_flags(self, text: str) -> list[str]:
        flags: list[str] = []
        for code, pattern in self._FLAG_PATTERNS.items():
            if pattern.search(text):
                flags.append(code)
        return flags
