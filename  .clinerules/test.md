# Testing Requirements

## 1. Strategy & Logic Testing
- **Mock Agents**: Test the LangGraph workflow using mocked LLM responses to ensure the state transitions (Analyst -> PM -> Risk) work correctly.
- **Logic Validation**: Test the `RiskGuard` with "fat-finger" scenarios (e.g., trying to buy $1M of stock with a $10k balance).

## 2. Execution Testing (Crucial)
- **Dry Run Mode**: Every exchange implementation must have a `paper_trading=True` mode. 
- **Mock Exchanges**: Use `unittest.mock` to simulate Exchange API responses (success, rate limit, timeout, insufficient funds).
- **Latency Check**: Log the time taken from "User Approval" to "Order Acknowledged".

## 3. Integration Testing
- **HITL Flow**: 
    1. Trigger a trade proposal.
    2. Verify it appears in the `PENDING` state in DB.
    3. Simulate a UI "Approve" click.
    4. Verify the `execution` module is called with correct parameters.

## 4. UI/UX Testing
- Verify that WebSocket reconnections handle network drops gracefully.
- Ensure the "Kill Switch" (Cancel all orders) is always responsive and has top priority.

## 5. Security
- Verify that `.env` files and API keys are never logged or exposed to the frontend.