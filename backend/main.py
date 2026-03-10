"""FastAPI main application for TradingAgents."""

import uuid
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import async_init_db, get_async_db, AsyncSessionLocal
from backend.models import (
    Proposal, Position, TradeHistory, AgentLog, User,
    ProposalStatus, TradeSide, PositionSide, ExchangeType, AgentType
)
from backend.schemas import (
    ProposalCreate, ProposalResponse, ProposalListResponse, ProposalApproval,
    PositionResponse, PositionListResponse, PositionClose, PortfolioSummary,
    TradeHistoryResponse, TradeHistoryListResponse,
    AgentRunRequest, AgentRunResponse,
    KillSwitchRequest, KillSwitchResponse,
    HealthResponse, ErrorResponse,
    AgentLogCreate, AgentLogResponse,
    WSProposalUpdate, WSPositionUpdate, WSAgentThinking, WSError,
    TradeSide as SchemaTradeSide,
    PositionSide as SchemaPositionSide,
    ExchangeType as SchemaExchangeType,
)

# Import TradingAgents
from tradingagents.graph.async_wrapper import AsyncTradingAgentsGraph, AsyncCallbackHandler, AgentEventType
from tradingagents.default_config import DEFAULT_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Version
VERSION = "0.1.0"

# Global state for kill switch
kill_switch_state = {
    "is_active": False,
    "activated_at": None,
    "activated_by": None,
    "reason": None,
}

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()


# Active agent runs tracking
active_runs: Dict[str, Dict[str, Any]] = {}


async def create_agent_callback(run_id: str, proposal_id: Optional[int] = None) -> AsyncCallbackHandler:
    """Create a callback handler for agent events that broadcasts to WebSocket."""
    handler = AsyncCallbackHandler()
    
    async def broadcast_event(event_type: str, data: Dict[str, Any]):
        """Broadcast agent event to all connected WebSocket clients."""
        message = {
            "type": "agent_event",
            "run_id": run_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        await manager.broadcast(message)
        
        # Log to database if proposal_id is provided
        if proposal_id and event_type in [AgentEventType.AGENT_THINKING, AgentEventType.AGENT_COMPLETE]:
            async with AsyncSessionLocal() as db:
                try:
                    # Map event types to agent types
                    agent_type_map = {
                        "market": AgentType.MARKET_ANALYST,
                        "sentiment": AgentType.SENTIMENT_ANALYST,
                        "news": AgentType.NEWS_ANALYST,
                        "fundamentals": AgentType.FUNDAMENTALS_ANALYST,
                        "bull": AgentType.BULL_RESEARCHER,
                        "bear": AgentType.BEAR_RESEARCHER,
                        "trader": AgentType.TRADER,
                        "risk_aggressive": AgentType.RISK_AGGRESSIVE,
                        "risk_conservative": AgentType.RISK_CONSERVATIVE,
                        "risk_neutral": AgentType.RISK_NEUTRAL,
                    }
                    
                    agent_type_str = data.get("agent", "unknown").lower()
                    agent_type = agent_type_map.get(agent_type_str, AgentType.TRADER)
                    
                    log = AgentLog(
                        proposal_id=proposal_id,
                        agent_type=agent_type,
                        agent_name=data.get("agent_name", agent_type_str),
                        message=data.get("message", ""),
                        reasoning=data.get("reasoning"),
                        action=data.get("action"),
                    )
                    db.add(log)
                    await db.commit()
                except Exception as e:
                    logger.error(f"Failed to log agent event: {e}")
    
    handler.add_callback(broadcast_event)
    return handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await async_init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="TradingAgents API - Multi-Agent LLM Financial Trading Framework",
    version=VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Exception Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ==================== Health Check ====================

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version=VERSION,
        database="connected",
        llm_provider=settings.llm_provider,
    )


# ==================== Agent Run ====================

async def _run_agent_task(
    run_id: str,
    symbol: str,
    trade_date: Optional[str],
    selected_analysts: List[str],
    exchange: str,
    auto_approve: bool,
    max_debate_rounds: int,
    max_risk_discuss_rounds: int,
):
    """
    Background task to run agent analysis.
    
    This runs in the background after the initial response is sent.
    """
    try:
        # Update run status
        active_runs[run_id]["status"] = "running"
        await manager.broadcast({
            "type": "run_status",
            "run_id": run_id,
            "status": "running",
        })
        
        # Parse trade date
        analysis_date = date.today()
        if trade_date:
            try:
                analysis_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid date format: {trade_date}, using today")
        
        # Build config
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = max_debate_rounds
        config["max_risk_discuss_rounds"] = max_risk_discuss_rounds
        
        # Create proposal placeholder first
        async with AsyncSessionLocal() as db:
            proposal = Proposal(
                symbol=symbol.upper(),
                side=TradeSide.BUY,  # Placeholder, will be updated
                quantity=0.0,  # Placeholder
                exchange=ExchangeType(exchange),
                status=ProposalStatus.PENDING,
                reasoning="Agent analysis in progress...",
            )
            db.add(proposal)
            await db.commit()
            await db.refresh(proposal)
            proposal_id = proposal.id
        
        # Update run with proposal_id
        active_runs[run_id]["proposal_id"] = proposal_id
        
        # Create callback handler
        callback = await create_agent_callback(run_id, proposal_id)
        
        # Initialize async agent graph
        async_graph = AsyncTradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=False,
            config=config,
            callback_handler=callback,
        )
        
        # Run the agent
        logger.info(f"Starting agent analysis for {symbol} on {analysis_date}")
        
        # Create proposal from agent output
        agent_proposal = await async_graph.create_proposal(
            company_name=symbol,
            trade_date=analysis_date,
            exchange=exchange,
        )
        
        # Update proposal with agent results
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Proposal).where(Proposal.id == proposal_id)
            )
            proposal = result.scalar_one_or_none()
            
            if proposal:
                # Parse side
                side_str = agent_proposal.get("side", "hold").lower()
                if side_str == "buy":
                    proposal.side = TradeSide.BUY
                elif side_str == "sell":
                    proposal.side = TradeSide.SELL
                else:
                    # Hold - mark as rejected with reason
                    proposal.status = ProposalStatus.REJECTED
                    proposal.rejection_reason = "Agent recommended HOLD - no action needed"
                    await db.commit()
                    active_runs[run_id]["status"] = "completed"
                    await manager.broadcast({
                        "type": "proposal_update",
                        "run_id": run_id,
                        "proposal": ProposalResponse.model_validate(proposal).model_dump()
                    })
                    return
                
                proposal.quantity = agent_proposal.get("quantity", 1.0)
                proposal.confidence = agent_proposal.get("confidence", 0.5)
                proposal.reasoning = agent_proposal.get("reasoning", "")
                proposal.market_report = agent_proposal.get("market_report", "")
                proposal.sentiment_report = agent_proposal.get("sentiment_report", "")
                proposal.news_report = agent_proposal.get("news_report", "")
                proposal.fundamentals_report = agent_proposal.get("fundamentals_report", "")
                proposal.investment_debate = agent_proposal.get("investment_debate", "")
                proposal.risk_debate = agent_proposal.get("risk_debate", "")
                
                if auto_approve:
                    proposal.status = ProposalStatus.APPROVED
                    proposal.approved_at = datetime.utcnow()
                    proposal.approved_by = "auto_approve"
                
                await db.commit()
                await db.refresh(proposal)
                
                # Broadcast final update
                await manager.broadcast({
                    "type": "proposal_update",
                    "run_id": run_id,
                    "proposal": ProposalResponse.model_validate(proposal).model_dump()
                })
        
        # Update run status
        active_runs[run_id]["status"] = "completed"
        await manager.broadcast({
            "type": "run_status",
            "run_id": run_id,
            "status": "completed",
            "proposal_id": proposal_id,
        })
        
        logger.info(f"Agent analysis completed for {symbol}, proposal_id={proposal_id}")
        
    except Exception as e:
        logger.error(f"Agent run error: {e}", exc_info=True)
        active_runs[run_id]["status"] = "failed"
        active_runs[run_id]["error"] = str(e)
        
        await manager.broadcast({
            "type": "run_status",
            "run_id": run_id,
            "status": "failed",
            "error": str(e),
        })
        
        # Update proposal if exists
        if proposal_id := active_runs[run_id].get("proposal_id"):
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = result.scalar_one_or_none()
                if proposal:
                    proposal.status = ProposalStatus.FAILED
                    proposal.execution_error = str(e)
                    proposal.reasoning = f"Agent analysis failed: {e}"
                    await db.commit()


@app.post("/api/agent/run", response_model=AgentRunResponse, tags=["Agent"])
async def run_agent(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Run agent analysis for a symbol.
    
    This endpoint triggers the TradingAgents framework to analyze the given symbol
    and generate a trade proposal. The proposal will be in PENDING status awaiting
    human approval (unless auto_approve is True).
    
    The analysis runs in the background. Use WebSocket to receive real-time updates.
    """
    # Check kill switch
    if kill_switch_state["is_active"]:
        raise HTTPException(status_code=403, detail="Kill switch is active. Agent execution is suspended.")
    
    run_id = str(uuid.uuid4())
    
    # Track the run
    active_runs[run_id] = {
        "symbol": request.symbol.upper(),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Start background task
    background_tasks.add_task(
        _run_agent_task,
        run_id=run_id,
        symbol=request.symbol.upper(),
        trade_date=request.trade_date,
        selected_analysts=request.selected_analysts,
        exchange=request.exchange.value,
        auto_approve=request.auto_approve,
        max_debate_rounds=request.max_debate_rounds,
        max_risk_discuss_rounds=request.max_risk_discuss_rounds,
    )
    
    return AgentRunResponse(
        run_id=run_id,
        symbol=request.symbol.upper(),
        status="pending",
        message="Agent analysis started. Connect to WebSocket for real-time updates.",
        proposal_id=None,
    )


@app.get("/api/agent/runs/{run_id}", tags=["Agent"])
async def get_run_status(run_id: str):
    """Get status of a specific agent run."""
    run_info = active_runs.get(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_info


# ==================== Proposals API ====================

@app.get("/api/proposals", response_model=ProposalListResponse, tags=["Proposals"])
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db),
):
    """List all trade proposals with optional filters."""
    query = select(Proposal)
    count_query = select(func.count(Proposal.id))
    
    if status:
        query = query.where(Proposal.status == ProposalStatus(status))
        count_query = count_query.where(Proposal.status == ProposalStatus(status))
    if symbol:
        query = query.where(Proposal.symbol == symbol.upper())
        count_query = count_query.where(Proposal.symbol == symbol.upper())
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(Proposal.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    proposals = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return ProposalListResponse(
        proposals=[ProposalResponse.model_validate(p) for p in proposals],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/proposals/{proposal_id}", response_model=ProposalResponse, tags=["Proposals"])
async def get_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific proposal by ID."""
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return ProposalResponse.model_validate(proposal)


@app.post("/api/proposals/{proposal_id}/approve", response_model=ProposalResponse, tags=["Proposals"])
async def approve_proposal(
    proposal_id: int,
    approval: ProposalApproval,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Approve or reject a trade proposal.
    
    This is the Human-in-the-Loop (HITL) approval endpoint.
    """
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Proposal is already {proposal.status.value}")
    
    if approval.approved:
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_at = datetime.utcnow()
        proposal.approved_by = "user"  # TODO: Get from auth
        
        # TODO: Execute the trade via execution layer
        # For now, just mark as approved
    else:
        proposal.status = ProposalStatus.REJECTED
        proposal.rejection_reason = approval.rejection_reason
    
    await db.commit()
    await db.refresh(proposal)
    
    # Broadcast update
    await manager.broadcast({
        "type": "proposal_update",
        "proposal": ProposalResponse.model_validate(proposal).model_dump()
    })
    
    return ProposalResponse.model_validate(proposal)


@app.post("/api/proposals/{proposal_id}/cancel", response_model=ProposalResponse, tags=["Proposals"])
async def cancel_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Cancel a pending proposal."""
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status not in [ProposalStatus.PENDING, ProposalStatus.APPROVED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel proposal with status {proposal.status.value}")
    
    proposal.status = ProposalStatus.CANCELLED
    await db.commit()
    await db.refresh(proposal)
    
    return ProposalResponse.model_validate(proposal)


# ==================== Positions API ====================

@app.get("/api/positions", response_model=PositionListResponse, tags=["Positions"])
async def list_positions(
    is_open: Optional[bool] = Query(None, description="Filter by open status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """List all positions with optional filters."""
    query = select(Position)
    count_query = select(func.count(Position.id))
    
    if is_open is not None:
        query = query.where(Position.is_open == is_open)
        count_query = count_query.where(Position.is_open == is_open)
    if symbol:
        query = query.where(Position.symbol == symbol.upper())
        count_query = count_query.where(Position.symbol == symbol.upper())
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(desc(Position.opened_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    positions = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PositionListResponse(
        positions=[PositionResponse.model_validate(p) for p in positions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/positions/summary", response_model=PortfolioSummary, tags=["Positions"])
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_async_db),
):
    """Get portfolio summary statistics."""
    # Get all open positions
    result = await db.execute(
        select(Position).where(Position.is_open == True)
    )
    positions = result.scalars().all()
    
    total_value = sum(p.quantity * (p.current_price or p.entry_price) for p in positions)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
    total_realized_pnl = sum(p.realized_pnl for p in positions)
    
    # Group by exchange
    positions_by_exchange = {}
    for p in positions:
        exchange = p.exchange.value
        positions_by_exchange[exchange] = positions_by_exchange.get(exchange, 0) + 1
    
    # Group by side
    positions_by_side = {}
    for p in positions:
        side = p.side.value
        positions_by_side[side] = positions_by_side.get(side, 0) + 1
    
    return PortfolioSummary(
        total_positions=len(positions),
        total_value=total_value,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=total_realized_pnl,
        positions_by_exchange=positions_by_exchange,
        positions_by_side=positions_by_side,
    )


@app.get("/api/positions/{position_id}", response_model=PositionResponse, tags=["Positions"])
async def get_position(
    position_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific position by ID."""
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return PositionResponse.model_validate(position)


@app.post("/api/positions/{position_id}/close", response_model=PositionResponse, tags=["Positions"])
async def close_position(
    position_id: int,
    close_request: PositionClose,
    db: AsyncSession = Depends(get_async_db),
):
    """Close an open position."""
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = result.scalar_one_or_none()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if not position.is_open:
        raise HTTPException(status_code=400, detail="Position is already closed")
    
    # Close the position
    position.is_open = False
    position.closed_at = datetime.utcnow()
    position.close_reason = close_request.reason or "manual_close"
    
    # Create trade history record
    trade = TradeHistory(
        symbol=position.symbol,
        side=TradeSide.SELL if position.side == PositionSide.LONG else TradeSide.BUY,
        quantity=position.quantity,
        price=position.current_price or position.entry_price,
        total_value=position.quantity * (position.current_price or position.entry_price),
        exchange=position.exchange,
        realized_pnl=position.unrealized_pnl,
        position_id=position.id,
    )
    db.add(trade)
    
    await db.commit()
    await db.refresh(position)
    
    # Broadcast update
    await manager.broadcast({
        "type": "position_update",
        "position": PositionResponse.model_validate(position).model_dump()
    })
    
    return PositionResponse.model_validate(position)


# ==================== Trade History API ====================

@app.get("/api/trades", response_model=TradeHistoryListResponse, tags=["Trade History"])
async def list_trades(
    symbol: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """List all trade history records."""
    query = select(TradeHistory)
    count_query = select(func.count(TradeHistory.id))
    
    if symbol:
        query = query.where(TradeHistory.symbol == symbol.upper())
        count_query = count_query.where(TradeHistory.symbol == symbol.upper())
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(desc(TradeHistory.executed_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return TradeHistoryListResponse(
        trades=[TradeHistoryResponse.model_validate(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==================== Kill Switch API ====================

@app.post("/api/kill-switch", response_model=KillSwitchResponse, tags=["System"])
async def activate_kill_switch(
    request: KillSwitchRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Activate the kill switch.
    
    When active, the kill switch prevents all agent execution and can optionally
    close all open positions.
    """
    global kill_switch_state
    
    kill_switch_state["is_active"] = True
    kill_switch_state["activated_at"] = datetime.utcnow()
    kill_switch_state["activated_by"] = "user"  # TODO: Get from auth
    kill_switch_state["reason"] = request.reason
    
    positions_closed = 0
    
    if request.close_all_positions:
        # Close all open positions
        result = await db.execute(
            select(Position).where(Position.is_open == True)
        )
        positions = result.scalars().all()
        
        for position in positions:
            position.is_open = False
            position.closed_at = datetime.utcnow()
            position.close_reason = "kill_switch"
            positions_closed += 1
        
        await db.commit()
    
    # Broadcast kill switch activation
    await manager.broadcast({
        "type": "kill_switch",
        "is_active": True,
        "positions_closed": positions_closed,
    })
    
    return KillSwitchResponse(
        is_active=True,
        activated_at=kill_switch_state["activated_at"],
        activated_by=kill_switch_state["activated_by"],
        reason=kill_switch_state["reason"],
        positions_closed=positions_closed,
    )


@app.delete("/api/kill-switch", response_model=KillSwitchResponse, tags=["System"])
async def deactivate_kill_switch():
    """Deactivate the kill switch."""
    global kill_switch_state
    
    kill_switch_state["is_active"] = False
    kill_switch_state["activated_at"] = None
    kill_switch_state["activated_by"] = None
    kill_switch_state["reason"] = None
    
    return KillSwitchResponse(is_active=False)


@app.get("/api/kill-switch", response_model=KillSwitchResponse, tags=["System"])
async def get_kill_switch_status():
    """Get current kill switch status."""
    return KillSwitchResponse(
        is_active=kill_switch_state["is_active"],
        activated_at=kill_switch_state["activated_at"],
        activated_by=kill_switch_state["activated_by"],
        reason=kill_switch_state["reason"],
    )


# ==================== Agent Logs API ====================

@app.get("/api/agent-logs", response_model=List[AgentLogResponse], tags=["Agent Logs"])
async def list_agent_logs(
    proposal_id: Optional[int] = Query(None),
    agent_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_db),
):
    """List agent logs with optional filters."""
    query = select(AgentLog)
    
    if proposal_id:
        query = query.where(AgentLog.proposal_id == proposal_id)
    if agent_type:
        query = query.where(AgentLog.agent_type == agent_type)
    
    query = query.order_by(desc(AgentLog.created_at)).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [AgentLogResponse.model_validate(log) for log in logs]


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Receives:
    - Agent thinking streams
    - Proposal updates
    - Position updates
    - Kill switch notifications
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Echo back or handle commands
            if data == "ping":
                await manager.send_personal({"type": "pong"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )