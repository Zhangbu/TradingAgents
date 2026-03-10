"""
TradingAgents API - FastAPI Application Entry Point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .database import init_db
from .routes import trading_router, analysis_router, system_router
from .schemas import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    print("🚀 Starting TradingAgents API...")
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down TradingAgents API...")


# Create FastAPI application
app = FastAPI(
    title="TradingAgents API",
    description="""
## TradingAgents - Multi-Agent AI Trading System API

A comprehensive trading system powered by multiple AI agents for stock analysis and trading.

### Features

- **Multi-Agent Analysis**: Fundamental, technical, news, and sentiment analysis
- **Automated Trading**: Paper and live trading support
- **Risk Management**: Stop-loss, take-profit, position sizing
- **Scheduling**: Automated analysis and rebalancing tasks
- **WebSocket Support**: Real-time updates and logs

### Modules

- **Trading**: Positions, orders, signals, account management
- **Analysis**: Run analysis, view reports, stock scanner
- **System**: Configuration, logs, scheduled tasks, status
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
        ).model_dump()
    )


# Include routers
app.include_router(trading_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(system_router, prefix="/api")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "TradingAgents API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


# API info endpoint
@app.get("/api", tags=["Root"])
async def api_info():
    """API information endpoint."""
    return {
        "name": "TradingAgents API",
        "version": "1.0.0",
        "endpoints": {
            "trading": "/api/trading",
            "analysis": "/api/analysis",
            "system": "/api/system",
        },
        "docs": "/docs"
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()