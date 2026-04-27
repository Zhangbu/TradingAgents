# TradingAgents Trading Platform Plan

## 1. Goals

Build a production-oriented trading platform on top of TradingAgents that:

- keeps the current multi-agent research workflow as the analysis core
- adds a web frontend for research, approval, and operations
- supports Alpaca and Interactive Brokers paper/live trading
- supports both manual and automated execution modes
- enforces strict, non-bypassable risk controls
- provides a full audit trail for every analysis, decision, and order event

## 2. Scope

### In Scope

- web-based analysis console
- backend APIs for tasks, reports, positions, orders, and approvals
- structured trade signal generation from existing TradingAgents outputs
- broker abstraction layer for Alpaca and IB
- paper trading first, then controlled live trading
- hard risk gates before order creation and before broker submission
- role-based operator workflow for approve/reject/cancel
- logging, monitoring, and event history

### Out of Scope for V1

- high-frequency or intraday market making
- options/futures/margin complexity in the first release
- portfolio optimization across many accounts
- unrestricted full-auto live trading on day one

## 3. Product Modes

The platform should expose explicit operating modes:

- `analysis_only`: run analysis, create reports, no order objects
- `paper_manual`: generate orders for paper accounts, require operator approval
- `paper_auto`: auto-execute in paper accounts after risk approval
- `live_manual`: create live orders only after operator approval
- `live_auto`: disabled by default, only enabled after extensive validation

Recommended rollout:

1. `analysis_only`
2. `paper_manual`
3. `paper_auto`
4. `live_manual`
5. `live_auto`

## 4. Architecture

### 4.1 Logical Layers

1. Research Layer
   - wraps current `TradingAgentsGraph`
   - produces research reports, supporting evidence, and a raw recommendation

2. Signal Layer
   - converts free-form LLM output into a strict structured signal
   - attaches confidence, horizon, entry idea, stop, take-profit, and sizing bounds

3. Risk Layer
   - validates account, symbol, market, position, and order constraints
   - decides allow / require approval / block

4. Execution Layer
   - converts approved intents into broker-native orders
   - tracks broker responses and reconciles account state

5. Operations Layer
   - frontend dashboards
   - scheduler
   - alerts
   - audit trail

### 4.2 Suggested Repository Layout

```text
docs/
  trading-platform-plan.md
backend/
  app/
    api/
      routes/
    core/
    db/
    models/
    schemas/
    services/
      analysis/
      signals/
      risk/
      execution/
      brokers/
      approvals/
      monitoring/
    workers/
frontend/
  app/
  components/
  features/
  lib/
shared/
  contracts/
  enums/
```

### 4.3 Runtime Components

- `frontend`: Next.js web UI
- `api`: FastAPI app
- `worker`: async jobs for analysis and reconciliation
- `postgres`: system of record
- `redis`: queue, cache, and transient coordination
- optional `scheduler`: APScheduler or worker-based scheduled jobs

## 5. Integration Strategy with Current TradingAgents

Current project state:

- existing LangGraph flow already produces analyst reports, trade proposal, and final decision
- current signal extraction only reduces text to one of `BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL`
- there is no persistent account state, broker state, or order lifecycle management

Required changes:

1. Keep the current analysis graph largely intact.
2. Add a structured output adapter after `final_trade_decision`.
3. Move from text-only decisions to machine-validated trade intents.
4. Do not allow LLM output to submit orders directly.

### 5.1 Structured Trade Intent

Target contract:

```json
{
  "symbol": "AAPL",
  "analysis_id": "uuid",
  "rating": "BUY",
  "side": "buy",
  "confidence": 0.78,
  "time_horizon": "swing",
  "entry_type": "limit",
  "entry_price": 201.5,
  "stop_loss": 194.0,
  "take_profit": 214.0,
  "max_position_pct": 0.05,
  "thesis_summary": "Momentum and fundamentals align.",
  "risk_flags": ["earnings_within_3_days"],
  "mode": "paper_manual"
}
```

### 5.2 Signal Conversion Rules

The signal service should:

- parse the final decision into a typed schema
- reject missing required fields
- clamp invalid numeric fields
- compute fallback defaults from account policy when optional fields are absent
- attach traceability to the source analysis artifacts

## 6. Broker Connectivity

### 6.1 Broker Abstraction

Define a shared interface such as:

- `get_account()`
- `get_positions()`
- `get_open_orders()`
- `submit_order(order_request)`
- `cancel_order(order_id)`
- `replace_order(order_id, order_request)`
- `get_order(order_id)`
- `sync_fills()`
- `is_market_open(symbol)`

### 6.2 Alpaca

Use Alpaca first because:

- paper trading is straightforward
- API ergonomics are simpler
- easier to validate the end-to-end order lifecycle

Modes:

- Alpaca paper in V1
- Alpaca live only after paper workflow is stable

### 6.3 Interactive Brokers

IB should be added after Alpaca paper is complete because:

- operational complexity is higher
- connectivity and session management are more fragile
- order type behavior and account models are more varied

Implementation note:

- prefer a dedicated IB adapter module with explicit connectivity health checks
- paper and live accounts must have separate credentials and environment isolation

## 7. Risk Management Design

Risk controls must be deterministic and enforced in code, not delegated to the LLM.

### 7.1 Account-Level Controls

- maximum gross exposure
- maximum net exposure
- maximum capital deployed per day
- daily realized + unrealized drawdown cap
- rolling max drawdown cap
- per-account max order count per interval
- trading session allowlist by market and timezone

### 7.2 Symbol-Level Controls

- maximum position size per symbol
- maximum sector exposure
- minimum average daily volume
- spread threshold
- volatility threshold
- earnings / macro event blackout windows
- restricted list / banned list

### 7.3 Order-Level Controls

- order notional limits
- max slippage from reference price
- limit-price sanity check
- duplicate order detection
- opposite-side conflict detection
- stale signal timeout
- stop-loss required for eligible strategies

### 7.4 Automation Controls

- live trading disabled by default
- dual confirmation for enabling `live_auto`
- automatic downgrade to `analysis_only` on repeated failures
- kill switch at account and global levels
- pause trading when broker sync is stale
- pause trading when position reconciliation fails

### 7.5 Human Approval Rules

Even after automation exists, require manual approval when:

- notional exceeds threshold
- exposure after order exceeds policy
- earnings or news risk window is active
- broker rejects and retry logic wants to resubmit
- confidence is below configured floor
- strategy enters a new symbol outside the approved watchlist

## 8. Data Model

Core tables:

- `users`
- `accounts`
- `broker_connections`
- `strategies`
- `watchlists`
- `analysis_runs`
- `analysis_artifacts`
- `trade_intents`
- `risk_checks`
- `approval_requests`
- `orders`
- `order_events`
- `fills`
- `positions`
- `position_snapshots`
- `pnl_snapshots`
- `alerts`
- `audit_logs`

### 8.1 Key Relationships

- one `analysis_run` can generate many `trade_intents`
- each `trade_intent` must have one or more `risk_checks`
- blocked intents never create orders
- approved intents can create one or more broker orders
- every order transition writes an `order_event`
- broker state is periodically reconciled into `positions` and `fills`

## 9. API Design

### 9.1 Analysis APIs

- `POST /api/analysis/runs`
- `GET /api/analysis/runs`
- `GET /api/analysis/runs/{id}`
- `GET /api/analysis/runs/{id}/artifacts`

### 9.2 Signal and Risk APIs

- `POST /api/trade-intents`
- `GET /api/trade-intents/{id}`
- `POST /api/trade-intents/{id}/risk-evaluate`
- `GET /api/trade-intents/{id}/risk-checks`

### 9.3 Approval APIs

- `GET /api/approvals`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`
- `POST /api/approvals/{id}/cancel`

### 9.4 Order and Position APIs

- `POST /api/orders/{intent_id}/submit`
- `POST /api/orders/{order_id}/cancel`
- `GET /api/orders`
- `GET /api/orders/{id}`
- `GET /api/positions`
- `GET /api/accounts/{id}/summary`

### 9.5 Broker Admin APIs

- `POST /api/brokers/{broker}/connect/test`
- `POST /api/brokers/{broker}/sync`
- `GET /api/brokers/{broker}/health`

## 10. Frontend Plan

### 10.1 Main Screens

- dashboard
  - account summary
  - open risk alerts
  - latest analyses
  - open orders and positions
- analysis workspace
  - symbol input
  - model/provider selection
  - analyst reports
  - structured signal
  - risk verdict
- approvals
  - pending actions
  - risk explanation
  - approve / reject / request rerun
- orders and positions
  - live lifecycle state
  - fills
  - stop levels
  - unrealized / realized PnL
- settings
  - broker connections
  - strategy rules
  - risk policies
  - automation mode

### 10.2 UX Rules

- always show current mode clearly: analysis, paper, or live
- live mode must have prominent warnings
- blocked trades must show exact risk reason
- all automated actions must be inspectable after the fact
- operators must be able to trace each order back to source analysis

## 11. Background Jobs

Required job classes:

- analysis execution job
- signal normalization job
- broker reconciliation job
- market session watcher
- risk watchdog
- alert delivery job
- end-of-day snapshot job

## 12. Observability

Minimum requirements:

- structured logs
- per-analysis trace IDs
- broker request correlation IDs
- metrics for success/failure/latency
- risk block counters by rule
- alerts for broker disconnect, sync lag, repeated order rejection, and drawdown breach

## 13. Security

- encrypt broker credentials and API secrets
- separate paper and live credentials
- role-based access control
- approval permissions separated from configuration permissions
- immutable audit logs for critical actions
- redaction of secrets in logs and UI

## 14. Delivery Phases

### Phase 1: Analysis Platform

Deliver:

- FastAPI skeleton
- Next.js skeleton
- analysis run persistence
- report viewing in web UI
- initial database schema

Exit criteria:

- user can trigger a TradingAgents analysis from the UI
- user can read saved reports and metadata

### Phase 2: Structured Signals and Risk Engine

Deliver:

- typed trade intent schema
- signal extraction service
- deterministic risk checks
- risk result UI

Exit criteria:

- every analysis can generate a valid or rejected trade intent
- blocked intents explain why

### Phase 3: Alpaca Paper Closed Loop

Deliver:

- Alpaca adapter
- account sync
- order submission/cancel flow
- manual approval workflow
- audit trail

Exit criteria:

- analysis -> intent -> risk -> approval -> paper order -> fill sync works end to end

### Phase 4: Automation and Guardrails

Deliver:

- scheduled analysis
- paper auto execution
- kill switch
- alerting
- reconciliation and stale-state safeguards

Exit criteria:

- paper auto mode can run safely with deterministic halts

### Phase 5: IB Paper and Controlled Live Rollout

Deliver:

- IB adapter
- live-manual workflow
- stricter operator controls
- staged rollout checklist

Exit criteria:

- both brokers work in paper mode
- live-manual works with complete audit coverage

## 15. Recommended Build Order

1. Create backend app skeleton and database foundation.
2. Add analysis run APIs around current `TradingAgentsGraph`.
3. Add frontend analysis workflow.
4. Implement typed signal contracts.
5. Implement risk engine and approval workflow.
6. Add Alpaca paper adapter and order lifecycle.
7. Add reconciliation, metrics, and alerts.
8. Add scheduling and automation controls.
9. Add IB adapter.
10. Add controlled live trading support.

## 16. Immediate Next Tasks

The next implementation cycle should focus on:

1. scaffolding `backend/app` and `frontend/`
2. defining shared enums and schemas for analysis, intents, risk, approvals, and orders
3. persisting analysis runs from TradingAgents into PostgreSQL
4. replacing the current text-only signal processor with a structured signal service
5. implementing the first deterministic risk policy set

## 17. Open Decisions

These decisions should be settled before coding too far:

- single-user first or multi-user from day one
- U.S. equities only in V1 or broader asset support
- whether `OVERWEIGHT` and `UNDERWEIGHT` map to trade actions or portfolio rebalance hints
- operator authentication approach
- whether live auto trading is in scope for the first production milestone

## 18. Recommendation

For the first working milestone, target:

- single-user
- U.S. equities only
- Alpaca paper only
- web UI
- manual approval required
- strict hard risk gates

This gives the fastest path to a safe closed loop without overcommitting to broker-specific complexity too early.
