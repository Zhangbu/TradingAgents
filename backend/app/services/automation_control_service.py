from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.automation import (
    LiveTradingConfirmRequest,
    LiveTradingRequest,
    AutomationHealthSnapshot,
    AutomationState,
    SchedulerUpdateRequest,
)
from backend.app.services.automation_state_repository import AutomationStateRepository


class AutomationControlService:
    """Manages kill switch, auto trading policy, sync health, and scheduler settings."""

    def __init__(self, repository: AutomationStateRepository) -> None:
        self.repository = repository

    def get_state(self) -> AutomationState:
        state = self.repository.load()
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def activate_kill_switch(self, reason: str) -> AutomationState:
        state = self.repository.load()
        state.kill_switch_active = True
        state.kill_switch_reason = reason
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def release_kill_switch(self) -> AutomationState:
        state = self.repository.load()
        state.kill_switch_active = False
        state.kill_switch_reason = None
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def set_auto_trading(self, enabled: bool) -> AutomationState:
        state = self.repository.load()
        state.auto_trading_enabled = enabled
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def set_live_trading(self, request: LiveTradingRequest) -> AutomationState:
        state = self.repository.load()
        state.live_trading_enabled = request.enabled
        if not request.enabled:
            state.live_trading_double_confirmed = False
            state.live_trading_unlocked_by = None
            state.live_trading_unlocked_at = None
        else:
            state.live_trading_unlocked_by = request.actor
            state.live_trading_unlocked_at = datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def confirm_live_trading(self, request: LiveTradingConfirmRequest) -> AutomationState:
        state = self.repository.load()
        if not state.live_trading_enabled:
            raise ValueError("Live trading must be enabled before it can be confirmed.")
        state.live_trading_double_confirmed = True
        state.live_trading_unlocked_by = request.actor
        state.live_trading_unlocked_at = datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def record_broker_sync(self, synced_at: datetime | None = None) -> AutomationState:
        state = self.repository.load()
        state.broker_sync_healthy = True
        state.last_broker_sync_at = synced_at or datetime.now(timezone.utc)
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def mark_broker_sync_unhealthy(self, reason: str) -> AutomationState:
        state = self.repository.load()
        state.broker_sync_healthy = False
        state.updated_at = datetime.now(timezone.utc)
        if not state.kill_switch_active:
            state.kill_switch_reason = reason
        return self.repository.save(state)

    def record_broker_success(self) -> AutomationState:
        state = self.repository.load()
        state.consecutive_broker_failures = 0
        state.broker_sync_healthy = True
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def record_broker_failure(self, reason: str) -> AutomationState:
        state = self.repository.load()
        state.consecutive_broker_failures += 1
        state.updated_at = datetime.now(timezone.utc)
        if state.consecutive_broker_failures >= state.max_consecutive_broker_failures:
            state.kill_switch_active = True
            state.kill_switch_reason = reason
        return self.repository.save(state)

    def update_scheduler(self, request: SchedulerUpdateRequest) -> AutomationState:
        state = self.repository.load()
        state.scheduler.enabled = request.enabled
        state.scheduler.interval_minutes = request.interval_minutes
        state.scheduler.target_mode = request.target_mode
        state.updated_at = datetime.now(timezone.utc)
        return self.repository.save(state)

    def get_health_snapshot(self, now: datetime | None = None) -> AutomationHealthSnapshot:
        state = self.repository.load()
        stale = self._is_sync_stale(state, now=now)
        effective_auto = (
            state.auto_trading_enabled
            and not state.kill_switch_active
            and state.broker_sync_healthy
            and not stale
        )
        effective_live = (
            state.live_trading_enabled
            and state.live_trading_double_confirmed
            and not state.kill_switch_active
            and state.broker_sync_healthy
            and not stale
        )

        if state.kill_switch_active:
            summary = f"Kill switch active: {state.kill_switch_reason or 'manual stop'}."
        elif stale:
            summary = "Broker sync is stale. Automated execution should remain paused."
        elif not state.broker_sync_healthy:
            summary = "Broker sync is unhealthy. Automated execution should remain paused."
        elif not state.auto_trading_enabled:
            summary = "Automation controls are healthy, but auto trading is disabled."
        else:
            summary = "Automation controls are healthy and auto trading is enabled."

        return AutomationHealthSnapshot(
            kill_switch_active=state.kill_switch_active,
            auto_trading_enabled=state.auto_trading_enabled,
            effective_auto_trading_enabled=effective_auto,
            effective_live_trading_enabled=effective_live,
            broker_sync_healthy=state.broker_sync_healthy,
            broker_sync_stale=stale,
            consecutive_broker_failures=state.consecutive_broker_failures,
            status_summary=summary,
            state=state,
        )

    def assert_submission_allowed(self, *, is_auto: bool, is_live: bool, action_label: str) -> None:
        snapshot = self.get_health_snapshot()

        if snapshot.kill_switch_active:
            raise ValueError(f"{action_label} is blocked because the kill switch is active.")
        if not snapshot.broker_sync_healthy:
            raise ValueError(f"{action_label} is blocked because broker sync is unhealthy.")
        if snapshot.broker_sync_stale:
            raise ValueError(f"{action_label} is blocked because broker sync is stale.")
        if is_auto and not snapshot.effective_auto_trading_enabled:
            raise ValueError(f"{action_label} is blocked because auto trading is disabled.")
        if is_live and not snapshot.effective_live_trading_enabled:
            raise ValueError(f"{action_label} is blocked because live trading is not fully enabled.")

    def _is_sync_stale(self, state: AutomationState, now: datetime | None = None) -> bool:
        if state.last_broker_sync_at is None:
            return True

        current_time = now or datetime.now(timezone.utc)
        age_seconds = (current_time - state.last_broker_sync_at).total_seconds()
        return age_seconds > state.sync_stale_after_seconds
