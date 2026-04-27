import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.analysis import (
    AnalysisArtifacts,
    AnalysisExecutionResult,
    AnalysisRequest,
    AnalysisStatus,
)
from backend.app.services.analysis_repository import AnalysisRepository
from backend.app.services.analysis_service import AnalysisService


class FakeRunner:
    def run(self, request: AnalysisRequest) -> AnalysisExecutionResult:
        return AnalysisExecutionResult(
            artifacts=AnalysisArtifacts(
                final_trade_decision=f"{request.symbol} BUY",
                processed_signal="BUY",
            )
        )


class FailingRunner:
    def run(self, request: AnalysisRequest) -> AnalysisExecutionResult:
        raise RuntimeError(f"runner failed for {request.symbol}")


class AnalysisServiceTest(unittest.TestCase):
    def test_create_run_marks_completed_when_runner_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository = AnalysisRepository(Path(tmp_dir))
            service = AnalysisService(repository=repository, runner=FakeRunner())
            request = AnalysisRequest(symbol="aapl")

            record = service.create_run(request)

            self.assertEqual(record.status, AnalysisStatus.completed)
            assert record.artifacts is not None
            self.assertEqual(record.symbol, "AAPL")
            self.assertEqual(record.artifacts.processed_signal, "BUY")

    def test_create_run_marks_failed_when_runner_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository = AnalysisRepository(Path(tmp_dir))
            service = AnalysisService(repository=repository, runner=FailingRunner())
            request = AnalysisRequest(symbol="tsla")

            record = service.create_run(request)

            self.assertEqual(record.status, AnalysisStatus.failed)
            self.assertIn("runner failed", record.error_message or "")


if __name__ == "__main__":
    unittest.main()
