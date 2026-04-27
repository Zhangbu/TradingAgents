# Alpaca Paper Runbook

This runbook covers the first real Alpaca paper-account validation flow for the TradingAgents platform branch.

## 1. Goal

Run the full Alpaca paper flow with your own credentials:

1. verify Alpaca paper connectivity
2. verify platform readiness for manual or automatic paper execution
3. create an analysis
4. generate a trade intent
5. run deterministic risk checks
6. create an order
7. approve it manually or let `paper_auto` submit directly
8. sync order state and inspect account state
9. review audit events

## 2. Required Environment

Backend environment variables:

```bash
export OPENAI_API_KEY=your_openai_key
export TRADINGAGENTS_ALPACA_ENABLED=true
export TRADINGAGENTS_ALPACA_PAPER_MODE=api
export ALPACA_API_KEY=your_alpaca_key
export ALPACA_SECRET_KEY=your_alpaca_secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
```

Optional local data path override:

```bash
export TRADINGAGENTS_PLATFORM_DATA_DIR=$HOME/.tradingagents/platform
```

## 3. Start the Backend

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## 4. Validate Alpaca Paper Connectivity First

Broker health:

```bash
curl http://127.0.0.1:8000/api/brokers/alpaca/health
```

Explicit connect test:

```bash
curl -X POST http://127.0.0.1:8000/api/brokers/alpaca/connect/test
```

Paper readiness:

```bash
curl http://127.0.0.1:8000/api/brokers/alpaca/paper-readiness
```

Expected checkpoints:

- `integration_mode` should be `api`
- `configured` should be `true`
- `credentials_present` should be `true`
- `connectivity_ok` should be `true`
- `manual_ready` should be `true` before testing manual submission
- `auto_ready` should be `true` before testing `paper_auto`

## 5. Refresh Broker Sync State

Record a fresh broker sync so automation controls do not stay stale:

```bash
curl -X POST http://127.0.0.1:8000/api/automation/broker-sync -H "Content-Type: application/json" -d '{}'
```

Enable auto trading only if you want to test `paper_auto`:

```bash
curl -X POST http://127.0.0.1:8000/api/automation/auto-trading -H "Content-Type: application/json" -d '{"enabled": true}'
```

## 6. Manual Alpaca Paper Flow

Create an analysis:

```bash
curl -X POST http://127.0.0.1:8000/api/analysis/runs \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "trade_date": "2026-04-26",
    "selected_analysts": ["market", "social", "news", "fundamentals"],
    "mode": "paper_manual"
  }'
```

Create a trade intent:

```bash
curl -X POST http://127.0.0.1:8000/api/trade-intents/from-analysis/<analysis_id>
```

Run risk evaluation:

```bash
curl -X POST http://127.0.0.1:8000/api/trade-intents/<intent_id>/risk-evaluate
```

Create the Alpaca paper order:

```bash
curl -X POST http://127.0.0.1:8000/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "intent_id": "<intent_id>",
    "broker_name": "alpaca",
    "broker_environment": "paper",
    "reference_price": 100
  }'
```

Approve the order:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/<order_id>/approve \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "<order_id>",
    "reviewer": "operator",
    "note": "manual alpaca paper check"
  }'
```

Sync the order:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/<order_id>/sync
```

Inspect the Alpaca paper account snapshot:

```bash
curl "http://127.0.0.1:8000/api/orders/accounts/paper?broker_name=alpaca"
```

Review audit events:

```bash
curl "http://127.0.0.1:8000/api/audit?entity_type=order&entity_id=<order_id>"
```

## 7. Automatic Alpaca Paper Flow

Use an analysis mode of `paper_auto`, then:

1. ensure `/api/brokers/alpaca/paper-readiness` returns `auto_ready: true`
2. create the analysis and trade intent
3. run risk evaluation
4. create the order

If the intent ends in `ready`, the platform should submit it directly to Alpaca paper without an approval step.

## 8. Troubleshooting

If `/api/brokers/alpaca/health` says simulator mode is active:

- confirm `TRADINGAGENTS_ALPACA_ENABLED=true`
- confirm `TRADINGAGENTS_ALPACA_PAPER_MODE=api`

If `configured=false`:

- check `ALPACA_API_KEY`
- check `ALPACA_SECRET_KEY`

If `manual_ready=false`:

- release the kill switch
- refresh broker sync
- confirm broker sync health is not stale

If `auto_ready=false`:

- enable auto trading
- verify the readiness endpoint no longer reports `auto_trading_enabled=false`

If order submission fails:

- inspect `status_reason` on the order
- inspect `/api/audit`
- inspect `/api/brokers/alpaca/health`

## 9. Current Phase 8 Limits

Phase 8 is designed to make Alpaca paper flow testable end to end, but it still does not include:

- real live-account rollout
- websocket streaming
- full broker-authoritative merge policy
- complete Interactive Brokers live connectivity
