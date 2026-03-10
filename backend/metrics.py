"""Prometheus metrics for TradingAgents."""

import logging
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create a custom registry
registry = CollectorRegistry()

# Proposal metrics
proposals_total = Counter(
    'trading_proposals_total',
    'Total number of trade proposals',
    ['status', 'symbol'],
    registry=registry
)

proposals_pending = Gauge(
    'trading_proposals_pending',
    'Number of pending proposals',
    registry=registry
)

# Trade execution metrics
trades_executed_total = Counter(
    'trading_trades_executed_total',
    'Total number of executed trades',
    ['exchange', 'side', 'symbol'],
    registry=registry
)

trade_execution_duration = Histogram(
    'trading_trade_execution_duration_seconds',
    'Time taken to execute a trade',
    ['exchange'],
    registry=registry
)

# Position metrics
positions_open = Gauge(
    'trading_positions_open',
    'Number of open positions',
    ['symbol', 'side'],
    registry=registry
)

position_pnl = Gauge(
    'trading_position_pnl',
    'Unrealized PnL of positions',
    ['symbol'],
    registry=registry
)

# Agent metrics
agent_runs_total = Counter(
    'trading_agent_runs_total',
    'Total number of agent analysis runs',
    ['status'],
    registry=registry
)

agent_run_duration = Histogram(
    'trading_agent_run_duration_seconds',
    'Time taken for agent analysis',
    registry=registry
)

agent_decisions = Counter(
    'trading_agent_decisions_total',
    'Agent decision counts',
    ['agent_type', 'decision'],
    registry=registry
)

# Risk metrics
risk_violations_total = Counter(
    'trading_risk_violations_total',
    'Total number of risk violations',
    ['violation_type'],
    registry=registry
)

kill_switch_activations = Counter(
    'trading_kill_switch_activations_total',
    'Number of kill switch activations',
    registry=registry
)

# API metrics
api_requests_total = Counter(
    'trading_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status'],
    registry=registry
)

api_request_duration = Histogram(
    'trading_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method'],
    registry=registry
)

# WebSocket metrics
websocket_connections = Gauge(
    'trading_websocket_connections',
    'Number of active WebSocket connections',
    registry=registry
)

websocket_messages_total = Counter(
    'trading_websocket_messages_total',
    'Total WebSocket messages',
    ['type'],
    registry=registry
)

# Exchange balance metrics
exchange_balance = Gauge(
    'trading_exchange_balance',
    'Exchange account balance',
    ['exchange', 'asset'],
    registry=registry
)


class MetricsService:
    """Service for recording and exposing metrics."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def record_proposal_created(self, symbol: str):
        """Record a new proposal."""
        proposals_total.labels(status='created', symbol=symbol).inc()
        proposals_pending.inc()
    
    def record_proposal_approved(self, symbol: str):
        """Record proposal approval."""
        proposals_total.labels(status='approved', symbol=symbol).inc()
        proposals_pending.dec()
    
    def record_proposal_rejected(self, symbol: str):
        """Record proposal rejection."""
        proposals_total.labels(status='rejected', symbol=symbol).inc()
        proposals_pending.dec()
    
    def record_trade_executed(self, exchange: str, side: str, symbol: str, duration: float):
        """Record a trade execution."""
        trades_executed_total.labels(exchange=exchange, side=side, symbol=symbol).inc()
        trade_execution_duration.labels(exchange=exchange).observe(duration)
    
    def update_positions(self, positions: list):
        """Update position gauges."""
        # Clear existing gauges
        positions_open.clear()
        position_pnl.clear()
        
        for pos in positions:
            positions_open.labels(
                symbol=pos.get('symbol', 'unknown'),
                side=pos.get('side', 'long')
            ).set(pos.get('quantity', 0))
            
            position_pnl.labels(
                symbol=pos.get('symbol', 'unknown')
            ).set(pos.get('unrealized_pnl', 0))
    
    def record_agent_run(self, status: str, duration: float):
        """Record an agent analysis run."""
        agent_runs_total.labels(status=status).inc()
        agent_run_duration.observe(duration)
    
    def record_agent_decision(self, agent_type: str, decision: str):
        """Record an agent decision."""
        agent_decisions.labels(agent_type=agent_type, decision=decision).inc()
    
    def record_risk_violation(self, violation_type: str):
        """Record a risk violation."""
        risk_violations_total.labels(violation_type=violation_type).inc()
    
    def record_kill_switch(self):
        """Record kill switch activation."""
        kill_switch_activations.inc()
    
    def record_api_request(self, endpoint: str, method: str, status: int, duration: float):
        """Record an API request."""
        api_requests_total.labels(endpoint=endpoint, method=method, status=status).inc()
        api_request_duration.labels(endpoint=endpoint, method=method).observe(duration)
    
    def set_websocket_connections(self, count: int):
        """Set WebSocket connection count."""
        websocket_connections.set(count)
    
    def record_websocket_message(self, message_type: str):
        """Record a WebSocket message."""
        websocket_messages_total.labels(type=message_type).inc()
    
    def update_exchange_balance(self, exchange: str, asset: str, balance: float):
        """Update exchange balance gauge."""
        exchange_balance.labels(exchange=exchange, asset=asset).set(balance)
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(registry).decode('utf-8')


# Global metrics service instance
metrics_service = MetricsService()