from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.order import OrderRecord


class OrderRepository:
    """Stores order records as JSON files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: OrderRecord) -> OrderRecord:
        path = self.base_dir / f"{record.id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get(self, order_id: str) -> OrderRecord | None:
        path = self.base_dir / f"{order_id}.json"
        if not path.exists():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        return OrderRecord.model_validate(payload)

    def list_orders(self, limit: int = 50) -> list[OrderRecord]:
        items: list[OrderRecord] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(OrderRecord.model_validate(payload))

        items.sort(key=lambda record: record.created_at, reverse=True)
        return items[:limit]
