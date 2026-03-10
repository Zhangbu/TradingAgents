"""Notification service for proposal and trade events."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    PROPOSAL_EXECUTED = "proposal_executed"
    PROPOSAL_FAILED = "proposal_failed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    AGENT_RUN_STARTED = "agent_run_started"
    AGENT_RUN_COMPLETED = "agent_run_completed"
    AGENT_RUN_FAILED = "agent_run_failed"


@dataclass
class Notification:
    """Notification data structure."""
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    read: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
        }


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self):
        # In-memory notification storage (use Redis in production)
        self._notifications: List[Notification] = []
        self._max_notifications = 100
        # WebSocket subscribers
        self._subscribers: Set[Any] = set()
    
    def subscribe(self, websocket: Any):
        """Subscribe a WebSocket connection to notifications."""
        self._subscribers.add(websocket)
        logger.info(f"WebSocket subscribed. Total subscribers: {len(self._subscribers)}")
    
    def unsubscribe(self, websocket: Any):
        """Unsubscribe a WebSocket connection."""
        self._subscribers.discard(websocket)
        logger.info(f"WebSocket unsubscribed. Total subscribers: {len(self._subscribers)}")
    
    async def broadcast(self, notification: Notification):
        """Broadcast notification to all subscribers."""
        message = json.dumps({
            "type": "notification",
            "payload": notification.to_dict(),
        })
        
        # Store notification
        self._notifications.append(notification)
        if len(self._notifications) > self._max_notifications:
            self._notifications = self._notifications[-self._max_notifications:]
        
        # Send to all subscribers
        disconnected = set()
        for ws in self._subscribers:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")
                disconnected.add(ws)
        
        # Clean up disconnected
        for ws in disconnected:
            self._subscribers.discard(ws)
        
        logger.info(f"Broadcasted {notification.type.value} to {len(self._subscribers)} subscribers")
    
    async def notify_proposal_created(self, proposal_id: int, symbol: str, side: str, quantity: float):
        """Notify about new proposal."""
        notification = Notification(
            type=NotificationType.PROPOSAL_CREATED,
            title="New Trade Proposal",
            message=f"New {side.upper()} proposal for {symbol} ({quantity} shares) awaiting approval.",
            data={
                "proposal_id": proposal_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
            },
        )
        await self.broadcast(notification)
    
    async def notify_proposal_approved(self, proposal_id: int, symbol: str, approved_by: str):
        """Notify about proposal approval."""
        notification = Notification(
            type=NotificationType.PROPOSAL_APPROVED,
            title="Proposal Approved",
            message=f"Proposal #{proposal_id} for {symbol} approved by {approved_by}.",
            data={
                "proposal_id": proposal_id,
                "symbol": symbol,
                "approved_by": approved_by,
            },
        )
        await self.broadcast(notification)
    
    async def notify_proposal_rejected(self, proposal_id: int, symbol: str, reason: str):
        """Notify about proposal rejection."""
        notification = Notification(
            type=NotificationType.PROPOSAL_REJECTED,
            title="Proposal Rejected",
            message=f"Proposal #{proposal_id} for {symbol} rejected. Reason: {reason}",
            data={
                "proposal_id": proposal_id,
                "symbol": symbol,
                "reason": reason,
            },
        )
        await self.broadcast(notification)
    
    async def notify_proposal_executed(self, proposal_id: int, symbol: str, price: float, order_id: str):
        """Notify about proposal execution."""
        notification = Notification(
            type=NotificationType.PROPOSAL_EXECUTED,
            title="Trade Executed",
            message=f"Proposal #{proposal_id} executed: {symbol} @ ${price:.2f}",
            data={
                "proposal_id": proposal_id,
                "symbol": symbol,
                "price": price,
                "order_id": order_id,
            },
        )
        await self.broadcast(notification)
    
    async def notify_position_opened(self, position_id: int, symbol: str, side: str, quantity: float, entry_price: float):
        """Notify about new position."""
        notification = Notification(
            type=NotificationType.POSITION_OPENED,
            title="Position Opened",
            message=f"New {side} position opened: {symbol} ({quantity} @ ${entry_price:.2f})",
            data={
                "position_id": position_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
            },
        )
        await self.broadcast(notification)
    
    async def notify_position_closed(self, position_id: int, symbol: str, pnl: float):
        """Notify about position closure."""
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        notification = Notification(
            type=NotificationType.POSITION_CLOSED,
            title="Position Closed",
            message=f"Position closed: {symbol}. PnL: {pnl_str}",
            data={
                "position_id": position_id,
                "symbol": symbol,
                "pnl": pnl,
            },
        )
        await self.broadcast(notification)
    
    async def notify_kill_switch(self, reason: str, positions_closed: int):
        """Notify about kill switch activation."""
        notification = Notification(
            type=NotificationType.KILL_SWITCH_ACTIVATED,
            title="Kill Switch Activated",
            message=f"Kill switch activated: {reason}. {positions_closed} positions closed.",
            data={
                "reason": reason,
                "positions_closed": positions_closed,
            },
        )
        await self.broadcast(notification)
    
    async def notify_agent_run(self, run_id: str, symbol: str, status: str, error: str = None):
        """Notify about agent run status."""
        if status == "started":
            notification = Notification(
                type=NotificationType.AGENT_RUN_STARTED,
                title="Agent Analysis Started",
                message=f"Starting analysis for {symbol}...",
                data={"run_id": run_id, "symbol": symbol},
            )
        elif status == "completed":
            notification = Notification(
                type=NotificationType.AGENT_RUN_COMPLETED,
                title="Agent Analysis Completed",
                message=f"Analysis completed for {symbol}.",
                data={"run_id": run_id, "symbol": symbol},
            )
        else:
            notification = Notification(
                type=NotificationType.AGENT_RUN_FAILED,
                title="Agent Analysis Failed",
                message=f"Analysis failed for {symbol}: {error}",
                data={"run_id": run_id, "symbol": symbol, "error": error},
            )
        await self.broadcast(notification)
    
    def get_notifications(self, limit: int = 20, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        notifications = self._notifications
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        return [n.to_dict() for n in notifications[-limit:]]
    
    def mark_read(self, notification_index: int):
        """Mark a notification as read."""
        if 0 <= notification_index < len(self._notifications):
            self._notifications[notification_index].read = True
    
    def mark_all_read(self):
        """Mark all notifications as read."""
        for n in self._notifications:
            n.read = True
    
    def unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self._notifications if not n.read)


# Global notification service instance
notification_service = NotificationService()