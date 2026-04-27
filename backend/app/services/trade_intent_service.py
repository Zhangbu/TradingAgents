from __future__ import annotations

from backend.app.schemas.trade_intent import TradeIntentRecord
from backend.app.services.analysis_repository import AnalysisRepository
from backend.app.services.risk_service import RiskService
from backend.app.services.signal_service import SignalService
from backend.app.services.trade_intent_repository import TradeIntentRepository


class TradeIntentService:
    """Creates and evaluates trade intents derived from analysis runs."""

    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        trade_intent_repository: TradeIntentRepository,
        signal_service: SignalService | None = None,
        risk_service: RiskService | None = None,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.trade_intent_repository = trade_intent_repository
        self.signal_service = signal_service or SignalService()
        self.risk_service = risk_service or RiskService()

    def create_from_analysis(self, analysis_id: str) -> TradeIntentRecord:
        analysis = self.analysis_repository.get(analysis_id)
        if analysis is None:
            raise ValueError("Analysis run not found.")

        intent = self.signal_service.build_from_analysis(analysis)
        return self.trade_intent_repository.save(intent)

    def evaluate_risk(self, intent_id: str) -> TradeIntentRecord:
        intent = self.trade_intent_repository.get(intent_id)
        if intent is None:
            raise ValueError("Trade intent not found.")

        evaluated = self.risk_service.evaluate(intent)
        return self.trade_intent_repository.save(evaluated)

    def get_intent(self, intent_id: str) -> TradeIntentRecord | None:
        return self.trade_intent_repository.get(intent_id)

    def list_intents(self, limit: int = 50) -> list[TradeIntentRecord]:
        return self.trade_intent_repository.list_intents(limit=limit)
