import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas.analysis import AnalysisArtifacts, AnalysisRunRecord, AnalysisStatus, PlatformMode
from backend.app.services.analysis_repository import AnalysisRepository


class AnalysisRepositoryTest(unittest.TestCase):
    def test_save_and_get_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository = AnalysisRepository(Path(tmp_dir))
            record = AnalysisRunRecord(
                symbol="AAPL",
                trade_date="2026-04-25",
                selected_analysts=["market", "news"],
                mode=PlatformMode.analysis_only,
                status=AnalysisStatus.completed,
                artifacts=AnalysisArtifacts(final_trade_decision="BUY"),
            )

            repository.save(record)
            loaded = repository.get(record.id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.id, record.id)
            self.assertEqual(loaded.artifacts.final_trade_decision, "BUY")

    def test_list_runs_is_sorted_by_created_at_desc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository = AnalysisRepository(Path(tmp_dir))
            older = AnalysisRunRecord(
                symbol="MSFT",
                trade_date="2026-04-24",
                selected_analysts=["market"],
                mode=PlatformMode.analysis_only,
                status=AnalysisStatus.completed,
                created_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
            )
            newer = AnalysisRunRecord(
                symbol="NVDA",
                trade_date="2026-04-25",
                selected_analysts=["market"],
                mode=PlatformMode.analysis_only,
                status=AnalysisStatus.completed,
                created_at=datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc),
            )

            repository.save(older)
            repository.save(newer)

            items = repository.list_runs()

            self.assertEqual(items[0].id, newer.id)
            self.assertEqual(items[1].id, older.id)


if __name__ == "__main__":
    unittest.main()
