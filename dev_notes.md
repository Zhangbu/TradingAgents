# Development Notes & Integration Guide

## 1. Environment Setup
- **Language**: Python 3.11+ (Backend), Node.js 18+ (Frontend).
- **Key Libraries**: 
  - `langgraph`: For agent workflow.
  - `fastapi`: For the web server.
  - `ccxt`: For crypto execution.
  - `futu-api`: For stock execution.
  - `pydantic-settings`: For secure config management.

## 2. Modified TradingAgents Logic
- The original `TradingAgents` uses a synchronous loop. We MUST wrap agent nodes in `async` functions to prevent blocking the FastAPI event loop.
- The `State` object in LangGraph should be extended to include:
  ```python
  class AgentState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], operator.add]
      proposal: Optional[TradeProposal]
      approval_required: bool
      execution_status: str
## 3. Database Schema (SQLite)
- proposals: id, symbol, side, size, price, reasoning, status (pending/approved/rejected), created_at.
- positions: symbol, entry_price, size, unrealized_pnl, exchange_name.
## 4. Critical Integration: Futu API
- Futu requires a running FutuOpenD gateway.
- Implementation must handle the TradeContext and QuoteContext initialization and keep-alive heartbeats.
## 5. Deployment Recommendation
- For local development: Use docker-compose to run the Backend, Frontend, and FutuOpenD (optional).      