# Architecture Decisions: AI Trading Platform

## 1. System Overview
A decoupled multi-agent trading system consisting of:
- **Decision Engine**: Modified `TradingAgents` logic using LangGraph.
- **Backend API**: FastAPI for state management, user authentication (minimal), and communication.
- **Execution Bridge**: A unified abstraction layer for Crypto (CCXT) and Stocks (Futu/IBKR).
- **Frontend**: React + Vite + Shadcn/UI for real-time monitoring and HITL (Human-in-the-loop) control.

## 2. Core Components
### A. The "Brain" (LangGraph)
- State-based transitions between agents (Analyst, Risk Manager, Portfolio Manager).
- Interruption points at the "Portfolio Manager" node for human approval.

### B. The "Bridge" (Execution Layer)
- `AbstractExchange`: Base class defining `get_price`, `place_order`, `get_balance`.
- `CCXTExchange`, `FutuExchange`: Concrete implementations.
- **Safety Valve**: A mandatory `RiskGuard` class that intercepts all orders before execution to check max position size and daily loss limits.

### C. State & Persistence
- **SQLite**: Stores trade logs, agent reasoning steps, and configuration.
- **WebSocket**: Real-time streaming of Agent "thinking" logs to the UI.

## 3. Communication Flow
1. **Agents** generate a `TradeProposal`.
2. **FastAPI** saves proposal to DB and sends a WebSocket alert.
3. **Frontend** prompts the user.
4. **User** sends `Approve`/`Reject` via REST API.
5. **Execution Bridge** executes trade upon approval.

## 4. Integration with TradingAgents
- We treat `TradingAgents` as a library. We extend its `State` to include `approval_status` and `execution_metadata`.