from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.audit import AuditLogRecord


class AuditLogRepository:
    """Stores audit log records as JSON files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: AuditLogRecord) -> AuditLogRecord:
        path = self.base_dir / f"{record.id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def list_logs(self, limit: int = 100, entity_type: str | None = None, entity_id: str | None = None) -> list[AuditLogRecord]:
        items: list[AuditLogRecord] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            record = AuditLogRecord.model_validate(payload)
            if entity_type and record.entity_type != entity_type:
                continue
            if entity_id and record.entity_id != entity_id:
                continue
            items.append(record)

        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[:limit]
