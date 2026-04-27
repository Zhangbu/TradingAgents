from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.broker import PaperBrokerState


class BrokerStateRepository:
    """Stores paper broker state in a single JSON file."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> PaperBrokerState:
        if not self.state_path.exists():
            return PaperBrokerState()

        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return PaperBrokerState.model_validate(payload)

    def save(self, state: PaperBrokerState) -> PaperBrokerState:
        self.state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state
