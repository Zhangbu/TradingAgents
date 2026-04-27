from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.config import get_settings
from backend.app.schemas.trade_intent import TradeIntentListResponse, TradeIntentRecord
from backend.app.services.analysis_repository import AnalysisRepository
from backend.app.services.trade_intent_repository import TradeIntentRepository
from backend.app.services.trade_intent_service import TradeIntentService

router = APIRouter(prefix="/trade-intents", tags=["trade-intents"])


def get_trade_intent_service() -> TradeIntentService:
    settings = get_settings()
    analysis_repository = AnalysisRepository(settings.analysis_runs_dir)
    trade_intent_repository = TradeIntentRepository(settings.trade_intents_dir)
    return TradeIntentService(
        analysis_repository=analysis_repository,
        trade_intent_repository=trade_intent_repository,
    )


@router.post("/from-analysis/{analysis_id}", response_model=TradeIntentRecord)
def create_trade_intent_from_analysis(analysis_id: str) -> TradeIntentRecord:
    try:
        return get_trade_intent_service().create_from_analysis(analysis_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{intent_id}/risk-evaluate", response_model=TradeIntentRecord)
def evaluate_trade_intent_risk(intent_id: str) -> TradeIntentRecord:
    try:
        return get_trade_intent_service().evaluate_risk(intent_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=TradeIntentListResponse)
def list_trade_intents(limit: int = Query(default=20, ge=1, le=200)) -> TradeIntentListResponse:
    items = get_trade_intent_service().list_intents(limit=limit)
    return TradeIntentListResponse(items=items)


@router.get("/{intent_id}", response_model=TradeIntentRecord)
def get_trade_intent(intent_id: str) -> TradeIntentRecord:
    record = get_trade_intent_service().get_intent(intent_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Trade intent not found")
    return record
