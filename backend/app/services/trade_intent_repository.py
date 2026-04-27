from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.trade_intent import TradeIntentRecord


class TradeIntentRepository:
    """Stores trade intents as JSON files."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: TradeIntentRecord) -> TradeIntentRecord:
        path = self.base_dir / f"{record.id}.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get(self, intent_id: str) -> TradeIntentRecord | None:
        path = self.base_dir / f"{intent_id}.json"
        if not path.exists():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        return TradeIntentRecord.model_validate(payload)

    def list_intents(self, limit: int = 50) -> list[TradeIntentRecord]:
        items: list[TradeIntentRecord] = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(TradeIntentRecord.model_validate(payload))

        items.sort(key=lambda record: record.created_at, reverse=True)
        return items[:limit]
