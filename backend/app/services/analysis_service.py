from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.schemas.analysis import (
    AnalysisExecutionResult,
    FailureDetails,
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
            data_vendors=request.data_vendors,
        )
        self.repository.save(record)

        try:
            result = self.runner.run(request)
            self._complete_run(record, result)
        except Exception as exc:  # pragma: no cover - exercised in service tests
            self._fail_run(record, *self._normalize_failure(str(exc)))

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

    def _fail_run(
        self,
        record: AnalysisRunRecord,
        error_message: str,
        failure_details: FailureDetails,
    ) -> None:
        record.status = AnalysisStatus.failed
        record.error_message = error_message
        record.failure_details = failure_details
        record.updated_at = datetime.now(timezone.utc)
        self.repository.save(record)

    def _normalize_failure(self, error_message: str) -> tuple[str, FailureDetails]:
        normalized = error_message.lower()

        if (
            "tls connect error" in normalized
            and "openssl_internal" in normalized
            and "curl" in normalized
        ):
            message = (
                "Market data fetch failed in the Yahoo Finance layer because the local "
                "curl/OpenSSL stack could not complete TLS setup. This usually comes "
                "from a newer yfinance + curl_cffi environment mismatch. Reinstall "
                "the project dependencies after pinning to the repo version, or switch "
                "the market data vendor away from yfinance before retrying."
            )
            return message, FailureDetails(
                code="market_data_tls",
                component="market_data",
                category="configuration",
                retryable=False,
                message=message,
                recommended_action=(
                    "Prefer alpha_vantage for now, or reinstall the pinned yfinance "
                    "stack before retrying."
                ),
                raw_message=error_message,
            )

        if "missing bearer or basic authentication" in normalized:
            message = (
                "The active language model provider rejected the request because the "
                "authorization header was missing. The configured provider key is "
                "likely absent, invalid, or not loaded into the running backend."
            )
            return message, FailureDetails(
                code="llm_auth",
                component="llm",
                category="credentials",
                retryable=False,
                message=message,
                recommended_action=(
                    "Check the active provider in runtime-profile, verify the "
                    "matching API key in .env, and restart the backend."
                ),
                raw_message=error_message,
            )

        if "rate limit" in normalized and "alpha vantage" in normalized:
            message = (
                "Alpha Vantage rate limited the market data request for this run."
            )
            return message, FailureDetails(
                code="market_data_rate_limit",
                component="market_data",
                category="rate_limit",
                retryable=True,
                message=message,
                recommended_action=(
                    "Wait for the vendor window to reset, or configure an explicit "
                    "multi-vendor fallback if you want automatic failover."
                ),
                raw_message=error_message,
            )

        if "api key" in normalized and "alpha vantage" in normalized:
            message = (
                "Alpha Vantage rejected the market data request because the API key "
                "is missing or invalid."
            )
            return message, FailureDetails(
                code="market_data_key_missing",
                component="market_data",
                category="credentials",
                retryable=False,
                message=message,
                recommended_action=(
                    "Set ALPHA_VANTAGE_API_KEY in .env and restart the backend."
                ),
                raw_message=error_message,
            )

        if "premium plan" in normalized and "alpha vantage" in normalized:
            message = (
                "Alpha Vantage rejected the market data request because the selected "
                "endpoint is only available on a premium plan."
            )
            return message, FailureDetails(
                code="market_data_premium_endpoint",
                component="market_data",
                category="configuration",
                retryable=False,
                message=message,
                recommended_action=(
                    "Switch the affected data vendor away from alpha_vantage for this "
                    "category, or upgrade the Alpha Vantage plan before retrying."
                ),
                raw_message=error_message,
            )

        failure = FailureDetails(
            code="analysis_unknown",
            component="analysis_runner",
            category="unknown",
            retryable=True,
            message=error_message,
            recommended_action=(
                "Inspect runtime-profile, runtime-health, and backend logs before retrying."
            ),
            raw_message=error_message,
        )
        return error_message, failure

    def _build_default_runner(self) -> Any:
        from backend.app.services.analysis_runner import TradingAgentsAnalysisRunner

        return TradingAgentsAnalysisRunner()
