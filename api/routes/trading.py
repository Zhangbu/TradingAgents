"""
Trading API routes - positions, orders, signals, account.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db, Position, Trade, Signal, AccountSnapshot
from ..schemas import (
    OrderRequest, SignalRequest, PositionUpdateRequest,
    PositionResponse, TradeResponse, SignalResponse, AccountResponse,
    SuccessResponse, ErrorResponse
)

router = APIRouter(prefix="/trading", tags=["Trading"])


# ==================== Account ====================

@router.get("/account", response_model=AccountResponse)
async def get_account(db: Session = Depends(get_db)):
    """Get account information."""
    # Get latest snapshot or create default
    latest = db.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_at.desc()).first()
    
    if latest:
        positions = db.query(Position).filter(Position.status == "open").all()
        positions_value = sum(
            (p.current_price or p.entry_price) * p.quantity 
            for p in positions
        )
        
        return AccountResponse(
            cash=latest.cash,
            equity=latest.equity,
            positions_value=positions_value,
            unrealized_pnl=latest.unrealized_pnl,
            realized_pnl=latest.realized_pnl,
            buying_power=latest.cash * 2,  # Assume 2x margin
            positions=[PositionResponse.model_validate(p) for p in positions]
        )
    
    # Default account
    return AccountResponse(
        cash=100000.0,
        equity=100000.0,
        positions_value=0.0,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        buying_power=200000.0,
        positions=[]
    )


# ==================== Positions ====================

@router.get("/positions", response_model=List[PositionResponse])
async def list_positions(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """List all positions."""
    query = db.query(Position)
    if status:
        query = query.filter(Position.status == status)
    return query.all()


@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(position_id: int, db: Session = Depends(get_db)):
    """Get a specific position."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


@router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    update: PositionUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update position stop loss / take profit."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if update.stop_loss is not None:
        position.stop_loss = update.stop_loss
    if update.take_profit is not None:
        position.take_profit = update.take_profit
    
    db.commit()
    db.refresh(position)
    return position


@router.delete("/positions/{position_id}", response_model=SuccessResponse)
async def close_position(position_id: int, db: Session = Depends(get_db)):
    """Close a position."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if position.status == "closed":
        raise HTTPException(status_code=400, detail="Position already closed")
    
    position.status = "closed"
    position.closed_at = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(message=f"Position {position_id} closed successfully")


# ==================== Orders ====================

@router.post("/orders", response_model=TradeResponse)
async def place_order(order: OrderRequest, db: Session = Depends(get_db)):
    """Place a new order."""
    # Create trade record
    trade = Trade(
        symbol=order.symbol.upper(),
        side=order.side.value,
        order_type=order.order_type.value,
        quantity=order.quantity,
        price=order.limit_price or 0.0,  # Will be updated on execution
        status="pending"
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    
    # TODO: Integrate with broker for actual execution
    # For now, mark as filled
    trade.status = "filled"
    trade.executed_at = datetime.utcnow()
    db.commit()
    
    return trade


@router.get("/orders", response_model=List[TradeResponse])
async def list_orders(
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """List orders/trades."""
    query = db.query(Trade)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    if status:
        query = query.filter(Trade.status == status)
    
    return query.order_by(Trade.executed_at.desc()).limit(limit).all()


@router.get("/orders/{order_id}", response_model=TradeResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a specific order."""
    trade = db.query(Trade).filter(Trade.id == order_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Order not found")
    return trade


# ==================== Signals ====================

@router.get("/signals", response_model=List[SignalResponse])
async def list_signals(
    symbol: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """List trading signals."""
    query = db.query(Signal)
    
    if symbol:
        query = query.filter(Signal.symbol == symbol.upper())
    if status:
        query = query.filter(Signal.status == status)
    
    return query.order_by(Signal.created_at.desc()).limit(limit).all()


@router.post("/signals", response_model=SignalResponse)
async def create_signal(signal: SignalRequest, db: Session = Depends(get_db)):
    """Create a new trading signal."""
    db_signal = Signal(
        symbol=signal.symbol.upper(),
        signal_type=signal.signal_type.value,
        confidence=signal.confidence,
        reason=signal.reason,
        source="manual"
    )
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal


@router.put("/signals/{signal_id}/execute", response_model=SignalResponse)
async def execute_signal(signal_id: int, db: Session = Depends(get_db)):
    """Mark a signal as executed."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.status = "executed"
    signal.executed_at = datetime.utcnow()
    db.commit()
    db.refresh(signal)
    return signal


@router.put("/signals/{signal_id}/ignore", response_model=SignalResponse)
async def ignore_signal(signal_id: int, db: Session = Depends(get_db)):
    """Mark a signal as ignored."""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.status = "ignored"
    db.commit()
    db.refresh(signal)
    return signal