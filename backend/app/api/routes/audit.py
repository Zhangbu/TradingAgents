from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.core.config import get_settings
from backend.app.schemas.audit import AuditLogListResponse
from backend.app.services.audit_log_repository import AuditLogRepository
from backend.app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit", tags=["audit"])


def get_audit_service() -> AuditLogService:
    settings = get_settings()
    return AuditLogService(AuditLogRepository(settings.audit_logs_dir))


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> AuditLogListResponse:
    items = get_audit_service().list_logs(limit=limit, entity_type=entity_type, entity_id=entity_id)
    return AuditLogListResponse(items=items)
