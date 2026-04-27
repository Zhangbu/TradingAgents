from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.analysis import AnalysisRunRecord


class AnalysisRepository:
    """Stores analysis runs as JSON files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: AnalysisRunRecord) -> AnalysisRunRecord:
        path = self.base_dir / f"{record.id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get(self, run_id: str) -> AnalysisRunRecord | None:
        path = self.base_dir / f"{run_id}.json"
        if not path.exists():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        return AnalysisRunRecord.model_validate(payload)

    def list_runs(self, limit: int = 50) -> list[AnalysisRunRecord]:
        records: list[AnalysisRunRecord] = []

        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(AnalysisRunRecord.model_validate(payload))

        records.sort(key=lambda record: record.created_at, reverse=True)
        return records[:limit]
