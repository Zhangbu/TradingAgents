import tempfile
import unittest
from pathlib import Path

from backend.app.schemas.audit import AuditEventType
from backend.app.services.audit_log_repository import AuditLogRepository
from backend.app.services.audit_log_service import AuditLogService


class AuditLogServiceTest(unittest.TestCase):
    def test_log_and_filter_audit_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            service = AuditLogService(AuditLogRepository(Path(tmp_dir)))
            service.log(
                event_type=AuditEventType.order_created,
                entity_type="order",
                entity_id="order-1",
                actor="tester",
                after={"status": "submitted"},
            )
            service.log(
                event_type=AuditEventType.order_rejected,
                entity_type="order",
                entity_id="order-2",
                actor="tester",
                after={"status": "rejected"},
            )

            filtered = service.list_logs(entity_type="order", entity_id="order-1")

            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0].event_type, AuditEventType.order_created)


if __name__ == "__main__":
    unittest.main()
