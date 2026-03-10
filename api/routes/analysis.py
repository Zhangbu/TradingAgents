"""
Analysis API routes - run analysis, get reports, scanner.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import asyncio

from ..database import get_db, AnalysisReport, Signal, SystemLog
from ..schemas import (
    AnalysisRequest, AnalysisResponse, ScannerRequest, ScannerResultResponse,
    SuccessResponse, SignalResponse
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# Store running analysis tasks
running_tasks: Dict[str, Any] = {}


async def run_analysis_task(
    symbol: str,
    date: str,
    analysts: List[str],
    research_depth: int,
    db: Session
):
    """Background task to run TradingAgents analysis."""
    try:
        # Log start
        log = SystemLog(
            level="info",
            module="analysis",
            message=f"Starting analysis for {symbol}"
        )
        db.add(log)
        db.commit()
        
        # Import TradingAgents
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        
        # Configure
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = research_depth
        config["max_risk_discuss_rounds"] = research_depth
        
        # Initialize graph
        ta = TradingAgentsGraph(debug=True, config=config)
        
        # Run analysis
        _, decision = ta.propagate(symbol, date)
        
        # Save reports
        # TODO: Extract individual reports from the decision
        
        # Create signal from decision
        # Parse decision to determine signal type
        signal_type = "hold"
        confidence = 0.5
        if "buy" in decision.lower():
            signal_type = "buy"
            confidence = 0.7
        elif "sell" in decision.lower():
            signal_type = "sell"
            confidence = 0.7
        
        signal = Signal(
            symbol=symbol.upper(),
            signal_type=signal_type,
            confidence=confidence,
            reason=decision[:500] if decision else None,
            source="agent"
        )
        db.add(signal)
        
        # Log completion
        log = SystemLog(
            level="info",
            module="analysis",
            message=f"Analysis completed for {symbol}"
        )
        db.add(log)
        db.commit()
        
        # Update running tasks
        if symbol in running_tasks:
            running_tasks[symbol]["status"] = "completed"
            running_tasks[symbol]["result"] = decision
            
    except Exception as e:
        # Log error
        log = SystemLog(
            level="error",
            module="analysis",
            message=f"Analysis failed for {symbol}: {str(e)}"
        )
        db.add(log)
        db.commit()
        
        if symbol in running_tasks:
            running_tasks[symbol]["status"] = "failed"
            running_tasks[symbol]["error"] = str(e)


@router.post("/run", response_model=SuccessResponse)
async def run_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run analysis on a symbol (async background task)."""
    symbol = request.symbol.upper()
    date = request.date or datetime.now().strftime("%Y-%m-%d")
    
    # Check if already running
    if symbol in running_tasks and running_tasks[symbol].get("status") == "running":
        raise HTTPException(status_code=400, detail=f"Analysis already running for {symbol}")
    
    # Mark as running
    running_tasks[symbol] = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "result": None
    }
    
    # Start background task
    background_tasks.add_task(
        run_analysis_task,
        symbol=symbol,
        date=date,
        analysts=request.analysts or ["market", "news", "fundamentals"],
        research_depth=request.research_depth or 1,
        db=SessionLocal()
    )
    
    from ..database import SessionLocal
    
    return SuccessResponse(
        message=f"Analysis started for {symbol}",
        data={"symbol": symbol, "date": date, "status": "running"}
    )


@router.get("/status/{symbol}", response_model=Dict[str, Any])
async def get_analysis_status(symbol: str):
    """Get status of running analysis."""
    symbol = symbol.upper()
    if symbol not in running_tasks:
        return {"symbol": symbol, "status": "not_found"}
    return {"symbol": symbol, **running_tasks[symbol]}


@router.get("/reports", response_model=List[AnalysisResponse])
async def list_reports(
    symbol: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """List analysis reports."""
    query = db.query(AnalysisReport)
    
    if symbol:
        query = query.filter(AnalysisReport.symbol == symbol.upper())
    
    reports = query.order_by(AnalysisReport.created_at.desc()).limit(limit).all()
    
    # Group by symbol and date
    grouped = {}
    for report in reports:
        key = f"{report.symbol}_{report.analysis_date}"
        if key not in grouped:
            grouped[key] = AnalysisResponse(
                symbol=report.symbol,
                date=report.analysis_date,
                decision=None,
                reports={},
                created_at=report.created_at
            )
        grouped[key].reports[report.report_type] = report.content or ""
    
    return list(grouped.values())


@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific analysis report."""
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ==================== Scanner ====================

@router.post("/scanner/run", response_model=List[ScannerResultResponse])
async def run_scanner(
    request: ScannerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run stock scanner with filters."""
    # Default watchlist if no symbols provided
    symbols = request.symbols or [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS"
    ]
    
    results = []
    
    # Simple scanner logic (can be enhanced)
    for symbol in symbols:
        # TODO: Implement actual scanning logic
        # For now, return mock results
        result = ScannerResultResponse(
            symbol=symbol,
            score=0.5,
            signals=["Price above MA50"],
            metrics={"price": 0, "volume": 0},
            recommendation="hold"
        )
        results.append(result)
    
    return results


@router.get("/scanner/watchlist")
async def get_watchlist(db: Session = Depends(get_db)):
    """Get current watchlist."""
    # TODO: Implement watchlist from database
    return {
        "symbols": [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"
        ]
    }


@router.post("/scanner/watchlist")
async def add_to_watchlist(
    symbol: str = Query(..., description="Symbol to add"),
    db: Session = Depends(get_db)
):
    """Add symbol to watchlist."""
    # TODO: Implement watchlist storage
    return SuccessResponse(message=f"{symbol.upper()} added to watchlist")