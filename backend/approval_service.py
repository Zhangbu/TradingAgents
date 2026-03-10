"""Approval service for HITL workflow."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import Proposal, ApprovalHistory, ProposalStatus
from backend.schemas import ProposalApprovalRequest
import logging

logger = logging.getLogger(__name__)


class ApprovalAction(str, Enum):
    """Approval action types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXECUTED = "executed"
    FAILED = "failed"


class ApprovalStateMachine:
    """State machine for proposal approval workflow."""
    
    # Valid state transitions
    TRANSITIONS = {
        ProposalStatus.PENDING: [
            ProposalStatus.APPROVED,
            ProposalStatus.REJECTED,
            ProposalStatus.CANCELLED,
        ],
        ProposalStatus.APPROVED: [
            ProposalStatus.EXECUTED,
            ProposalStatus.FAILED,
            ProposalStatus.CANCELLED,
        ],
        ProposalStatus.REJECTED: [],  # Terminal state
        ProposalStatus.EXECUTED: [],   # Terminal state
        ProposalStatus.FAILED: [
            ProposalStatus.PENDING,  # Can retry
        ],
        ProposalStatus.CANCELLED: [],  # Terminal state
    }
    
    @classmethod
    def can_transition(cls, current: ProposalStatus, target: ProposalStatus) -> bool:
        """Check if transition is valid."""
        return target in cls.TRANSITIONS.get(current, [])
    
    @classmethod
    def get_valid_transitions(cls, current: ProposalStatus) -> List[ProposalStatus]:
        """Get all valid transitions from current state."""
        return cls.TRANSITIONS.get(current, [])


class ApprovalService:
    """Service for managing proposal approvals."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def approve(
        self,
        proposal_id: int,
        request: ProposalApprovalRequest,
        actor: Optional[str] = None
    ) -> Proposal:
        """Approve or reject a proposal."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        previous_status = proposal.status
        
        if request.approved:
            # Approve the proposal
            if not ApprovalStateMachine.can_transition(
                previous_status, ProposalStatus.APPROVED
            ):
                raise ValueError(
                    f"Cannot approve proposal in {previous_status.value} state"
                )
            
            proposal.status = ProposalStatus.APPROVED
            proposal.approved_by = actor or "system"
            proposal.approved_at = datetime.utcnow()
            
            # Create approval history
            history = ApprovalHistory(
                proposal_id=proposal_id,
                action=ApprovalAction.APPROVED.value,
                actor=actor,
                previous_status=previous_status,
                new_status=ProposalStatus.APPROVED,
            )
            self.db.add(history)
            
            logger.info(f"Proposal {proposal_id} approved by {actor}")
            
        else:
            # Reject the proposal
            if not ApprovalStateMachine.can_transition(
                previous_status, ProposalStatus.REJECTED
            ):
                raise ValueError(
                    f"Cannot reject proposal in {previous_status.value} state"
                )
            
            proposal.status = ProposalStatus.REJECTED
            proposal.rejection_reason = request.rejection_reason
            
            # Create rejection history
            history = ApprovalHistory(
                proposal_id=proposal_id,
                action=ApprovalAction.REJECTED.value,
                actor=actor,
                reason=request.rejection_reason,
                previous_status=previous_status,
                new_status=ProposalStatus.REJECTED,
            )
            self.db.add(history)
            
            logger.info(f"Proposal {proposal_id} rejected by {actor}: {request.rejection_reason}")
        
        await self.db.commit()
        await self.db.refresh(proposal)
        
        return proposal
    
    async def mark_executed(
        self,
        proposal_id: int,
        executed_price: float,
        order_id: Optional[str] = None
    ) -> Proposal:
        """Mark proposal as executed after trade completion."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        previous_status = proposal.status
        
        if not ApprovalStateMachine.can_transition(
            previous_status, ProposalStatus.EXECUTED
        ):
            raise ValueError(
                f"Cannot execute proposal in {previous_status.value} state"
            )
        
        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_price = executed_price
        proposal.executed_at = datetime.utcnow()
        proposal.order_id = order_id
        
        # Create execution history
        history = ApprovalHistory(
            proposal_id=proposal_id,
            action=ApprovalAction.EXECUTED.value,
            previous_status=previous_status,
            new_status=ProposalStatus.EXECUTED,
        )
        self.db.add(history)
        
        await self.db.commit()
        await self.db.refresh(proposal)
        
        logger.info(f"Proposal {proposal_id} executed at {executed_price}")
        
        return proposal
    
    async def mark_failed(
        self,
        proposal_id: int,
        error: str
    ) -> Proposal:
        """Mark proposal as failed."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        previous_status = proposal.status
        
        if not ApprovalStateMachine.can_transition(
            previous_status, ProposalStatus.FAILED
        ):
            raise ValueError(
                f"Cannot fail proposal in {previous_status.value} state"
            )
        
        proposal.status = ProposalStatus.FAILED
        proposal.execution_error = error
        
        # Create failure history
        history = ApprovalHistory(
            proposal_id=proposal_id,
            action=ApprovalAction.FAILED.value,
            reason=error,
            previous_status=previous_status,
            new_status=ProposalStatus.FAILED,
        )
        self.db.add(history)
        
        await self.db.commit()
        await self.db.refresh(proposal)
        
        logger.error(f"Proposal {proposal_id} failed: {error}")
        
        return proposal
    
    async def cancel(
        self,
        proposal_id: int,
        reason: Optional[str] = None,
        actor: Optional[str] = None
    ) -> Proposal:
        """Cancel a proposal."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        previous_status = proposal.status
        
        if not ApprovalStateMachine.can_transition(
            previous_status, ProposalStatus.CANCELLED
        ):
            raise ValueError(
                f"Cannot cancel proposal in {previous_status.value} state"
            )
        
        proposal.status = ProposalStatus.CANCELLED
        
        # Create cancellation history
        history = ApprovalHistory(
            proposal_id=proposal_id,
            action=ApprovalAction.CANCELLED.value,
            actor=actor,
            reason=reason,
            previous_status=previous_status,
            new_status=ProposalStatus.CANCELLED,
        )
        self.db.add(history)
        
        await self.db.commit()
        await self.db.refresh(proposal)
        
        logger.info(f"Proposal {proposal_id} cancelled by {actor}: {reason}")
        
        return proposal
    
    async def get_history(self, proposal_id: int) -> List[ApprovalHistory]:
        """Get approval history for a proposal."""
        result = await self.db.execute(
            select(ApprovalHistory)
            .where(ApprovalHistory.proposal_id == proposal_id)
            .order_by(ApprovalHistory.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_pending_count(self) -> int:
        """Get count of pending proposals."""
        result = await self.db.execute(
            select(Proposal).where(Proposal.status == ProposalStatus.PENDING)
        )
        return len(list(result.scalars().all()))