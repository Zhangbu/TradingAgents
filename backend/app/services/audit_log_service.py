from __future__ import annotations

from typing import Any

from backend.app.schemas.audit import AuditEventType, AuditLogRecord
from backend.app.services.audit_log_repository import AuditLogRepository


class AuditLogService:
    """Writes and queries audit events."""

    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    def log(
        self,
        *,
        event_type: AuditEventType,
        entity_type: str,
        entity_id: str,
        actor: str,
        before: Any = None,
        after: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogRecord:
        record = AuditLogRecord(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            before=self._normalize(before),
            after=self._normalize(after),
            metadata=metadata or {},
        )
        return self.repository.save(record)

    def list_logs(self, limit: int = 100, entity_type: str | None = None, entity_id: str | None = None) -> list[AuditLogRecord]:
        return self.repository.list_logs(limit=limit, entity_type=entity_type, entity_id=entity_id)

    def _normalize(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return value
        return {"value": repr(value)}
