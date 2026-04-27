from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.config import get_settings
from backend.app.schemas.analysis import AnalysisRequest, AnalysisRunListResponse, AnalysisRunRecord
from backend.app.services.analysis_repository import AnalysisRepository
from backend.app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_analysis_service() -> AnalysisService:
    settings = get_settings()
    repository = AnalysisRepository(settings.analysis_runs_dir)
    return AnalysisService(repository=repository)


@router.post("/runs", response_model=AnalysisRunRecord)
def create_analysis_run(request: AnalysisRequest) -> AnalysisRunRecord:
    return get_analysis_service().create_run(request)


@router.get("/runs", response_model=AnalysisRunListResponse)
def list_analysis_runs(limit: int = Query(default=20, ge=1, le=200)) -> AnalysisRunListResponse:
    items = get_analysis_service().list_runs(limit=limit)
    return AnalysisRunListResponse(items=items)


@router.get("/runs/{run_id}", response_model=AnalysisRunRecord)
def get_analysis_run(run_id: str) -> AnalysisRunRecord:
    record = get_analysis_service().get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return record
