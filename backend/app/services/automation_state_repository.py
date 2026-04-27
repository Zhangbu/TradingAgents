from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas.automation import AutomationState


class AutomationStateRepository:
    """Stores automation and guardrail state in a JSON file."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AutomationState:
        if not self.state_path.exists():
            return AutomationState()

        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return AutomationState.model_validate(payload)

    def save(self, state: AutomationState) -> AutomationState:
        self.state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        return state
