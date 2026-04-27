from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.schemas.analysis import (
    AnalysisExecutionResult,
    AnalysisRequest,
    AnalysisRunRecord,
    AnalysisStatus,
)
from backend.app.services.analysis_repository import AnalysisRepository


class AnalysisService:
    """Coordinates analysis execution and persistence."""

    def __init__(
        self,
        repository: AnalysisRepository,
        runner: Any | None = None,
    ) -> None:
        self.repository = repository
        self.runner = runner or self._build_default_runner()

    def create_run(self, request: AnalysisRequest) -> AnalysisRunRecord:
        record = AnalysisRunRecord(
            symbol=request.symbol.upper(),
            trade_date=request.trade_date,
            selected_analysts=request.selected_analysts,
            mode=request.mode,
            status=AnalysisStatus.running,
            llm_provider=request.llm_provider,
            deep_think_llm=request.deep_think_llm,
            quick_think_llm=request.quick_think_llm,
        )
        self.repository.save(record)

        try:
            result = self.runner.run(request)
            self._complete_run(record, result)
        except Exception as exc:  # pragma: no cover - exercised in service tests
            self._fail_run(record, str(exc))

        return self.repository.get(record.id) or record

    def list_runs(self, limit: int = 50) -> list[AnalysisRunRecord]:
        return self.repository.list_runs(limit=limit)

    def get_run(self, run_id: str) -> AnalysisRunRecord | None:
        return self.repository.get(run_id)

    def _complete_run(
        self,
        record: AnalysisRunRecord,
        result: AnalysisExecutionResult,
    ) -> None:
        record.status = AnalysisStatus.completed
        record.artifacts = result.artifacts
        record.updated_at = datetime.now(timezone.utc)
        self.repository.save(record)

    def _fail_run(self, record: AnalysisRunRecord, error_message: str) -> None:
        record.status = AnalysisStatus.failed
        record.error_message = error_message
        record.updated_at = datetime.now(timezone.utc)
        self.repository.save(record)

    def _build_default_runner(self) -> Any:
        from backend.app.services.analysis_runner import TradingAgentsAnalysisRunner

        return TradingAgentsAnalysisRunner()
