export const defaultAnalysisRequest = {
  symbol: "AAPL",
  trade_date: "2026-04-25",
  selected_analysts: ["market", "social", "news", "fundamentals"],
  mode: "analysis_only",
};

export const analysisEndpointExample = "POST /api/analysis/runs";

export type PlatformMode =
  | "analysis_only"
  | "paper_manual"
  | "paper_auto"
  | "live_manual"
  | "live_auto";

export type AnalysisStatus = "queued" | "running" | "completed" | "failed";

export interface AnalysisRequest {
  symbol: string;
  trade_date?: string;
  selected_analysts: string[];
  llm_provider?: string;
  deep_think_llm?: string;
  quick_think_llm?: string;
  data_vendors?: Record<string, string>;
  max_debate_rounds?: number;
  max_risk_discuss_rounds?: number;
  mode: PlatformMode;
}

export interface AnalysisArtifacts {
  market_report?: string;
  sentiment_report?: string;
  news_report?: string;
  fundamentals_report?: string;
  investment_plan?: string;
  trader_investment_plan?: string;
  final_trade_decision?: string;
  processed_signal?: string;
}

export interface AnalysisRunRecord {
  id: string;
  symbol: string;
  trade_date?: string;
  selected_analysts: string[];
  mode: PlatformMode;
  status: AnalysisStatus;
  created_at: string;
  updated_at: string;
  llm_provider?: string;
  deep_think_llm?: string;
  quick_think_llm?: string;
  data_vendors?: Record<string, string>;
  error_message?: string;
  failure_details?: FailureDetails;
  artifacts?: AnalysisArtifacts;
}

export interface FailureDetails {
  code: string;
  component: string;
  category: string;
  retryable: boolean;
  message: string;
  recommended_action?: string;
  raw_message?: string;
}

export type TradeRating = "BUY" | "OVERWEIGHT" | "HOLD" | "UNDERWEIGHT" | "SELL";
export type TradeSide = "buy" | "sell" | "hold";
export type TradeIntentStatus = "draft" | "ready" | "blocked" | "approval_required";
export type RiskSeverity = "info" | "warning" | "critical";
export type RiskOutcome = "pass" | "require_approval" | "block";

export interface RiskCheck {
  rule_code: string;
  severity: RiskSeverity;
  outcome: RiskOutcome;
  message: string;
}

export interface RiskSummary {
  outcome: TradeIntentStatus;
  checks: RiskCheck[];
}

export interface TradeIntentRecord {
  id: string;
  analysis_id: string;
  symbol: string;
  trade_date?: string;
  mode: PlatformMode;
  rating: TradeRating;
  side: TradeSide;
  status: TradeIntentStatus;
  confidence: number;
  entry_type: "market" | "limit" | "none";
  time_horizon: "intraday" | "swing" | "position";
  max_position_pct: number;
  max_loss_pct: number;
  take_profit_pct: number;
  thesis_summary: string;
  source_signal?: string;
  risk_flags: string[];
  risk_summary?: RiskSummary;
}

export interface OrderRecord {
  id: string;
  intent_id: string;
  analysis_id: string;
  symbol: string;
  broker_name: "alpaca" | "interactive_brokers";
  broker_environment: "paper" | "live";
  side: "buy" | "sell";
  order_type: "market" | "limit";
  quantity: number;
  filled_quantity?: number;
  remaining_quantity?: number;
  broker_order_id?: string;
  requested_price?: number;
  filled_price?: number;
  average_fill_price?: number;
  broker_status_raw?: string;
  status:
    | "pending_approval"
    | "approved"
    | "rejected"
    | "submitted"
    | "partially_filled"
    | "filled"
    | "cancel_requested"
    | "canceled"
    | "replace_requested"
    | "replaced"
    | "expired"
    | "failed";
  status_reason?: string;
  failure_details?: FailureDetails;
  approval_required: boolean;
  cancel_requested_at?: string;
  canceled_at?: string;
  submitted_at?: string;
  filled_at?: string;
  last_synced_at?: string;
  created_at?: string;
  updated_at?: string;
  broker_updated_at?: string;
}

export interface AccountSnapshot {
  cash: number;
  equity: number;
  buying_power: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    average_price: number;
    market_value: number;
  }>;
}

export interface BrokerSyncResult {
  synced_orders: OrderRecord[];
  account_snapshot?: AccountSnapshot | null;
  matched_positions: Array<{
    symbol: string;
    quantity: number;
    average_price: number;
    market_value: number;
  }>;
  unmatched_local_symbols: string[];
  unmatched_broker_symbols: string[];
  order_diffs: ReconciliationDiff[];
  position_diffs: ReconciliationDiff[];
  account_diffs: ReconciliationDiff[];
  cash_diff: number;
  equity_diff: number;
  requires_operator_review: boolean;
  summary_message?: string;
  failure_details?: FailureDetails | null;
}

export interface ReconciliationDiff {
  category: string;
  field: string;
  severity: string;
  local_value?: string | number | null;
  broker_value?: string | number | null;
  message: string;
}

export interface AutomationState {
  kill_switch_active: boolean;
  kill_switch_reason?: string;
  auto_trading_enabled: boolean;
  live_trading_enabled?: boolean;
  live_trading_double_confirmed?: boolean;
  live_trading_unlocked_by?: string;
  live_trading_unlocked_at?: string;
  broker_sync_healthy: boolean;
  last_broker_sync_at?: string;
  sync_stale_after_seconds: number;
  consecutive_broker_failures: number;
  max_consecutive_broker_failures: number;
  scheduler: {
    enabled: boolean;
    interval_minutes: number;
    target_mode: string;
  };
}

export interface AutomationHealthSnapshot {
  kill_switch_active: boolean;
  auto_trading_enabled: boolean;
  effective_auto_trading_enabled: boolean;
  effective_live_trading_enabled: boolean;
  broker_sync_healthy: boolean;
  broker_sync_stale: boolean;
  consecutive_broker_failures: number;
  status_summary: string;
  state: AutomationState;
}

export interface BrokerHealthCheckResult {
  broker_name: string;
  environment: "paper" | "live" | string;
  integration_mode: "simulator" | "api" | string;
  configured: boolean;
  credentials_present: boolean;
  connectivity_ok: boolean;
  message: string;
  base_url?: string;
  account_snapshot?: AccountSnapshot;
  checked_at: string;
}

export interface AlpacaPaperReadiness {
  broker_health: BrokerHealthCheckResult;
  automation_health: AutomationHealthSnapshot;
  manual_ready: boolean;
  auto_ready: boolean;
  checklist: string[];
}

export type RuntimeHealthState = "healthy" | "warning" | "blocked";

export interface AnalysisRuntimeProfile {
  llm_provider: string;
  deep_think_llm: string;
  quick_think_llm: string;
  backend_url?: string;
  data_vendors: Record<string, string>;
  vendor_fallback_policy: string;
  api_keys_present: Record<string, boolean>;
}

export interface RuntimeModelOption {
  label: string;
  value: string;
}

export interface RuntimeProviderCatalog {
  provider: string;
  backend_url?: string;
  api_key_env?: string;
  quick_models: RuntimeModelOption[];
  deep_models: RuntimeModelOption[];
}

export interface RuntimeDataVendorCategory {
  category: string;
  label: string;
  current_vendor: string;
  options: string[];
}

export interface AnalysisRuntimeCatalog {
  providers: Record<string, RuntimeProviderCatalog>;
  data_vendor_categories: RuntimeDataVendorCategory[];
  known_data_vendors: string[];
  vendor_fallback_policy: string;
}

export interface RuntimeHealthCheck {
  component: string;
  state: RuntimeHealthState;
  configured: boolean;
  healthy: boolean;
  message: string;
  recommended_action?: string;
}

export interface AnalysisRuntimeHealth {
  profile: AnalysisRuntimeProfile;
  llm: RuntimeHealthCheck;
  market_data: RuntimeHealthCheck;
}

export interface WorkflowPreflight {
  workflow: string;
  ready: boolean;
  state: RuntimeHealthState;
  checks: RuntimeHealthCheck[];
  blocker_count: number;
  warning_count: number;
}

export interface PlatformPreflightSummary {
  analysis: WorkflowPreflight;
  paper_manual: WorkflowPreflight;
  paper_auto: WorkflowPreflight;
}

export type AuditEventType =
  | "trade_intent_created"
  | "risk_evaluated"
  | "order_created"
  | "order_approved"
  | "order_rejected"
  | "order_canceled"
  | "order_replaced"
  | "broker_synced"
  | "reconciliation_completed"
  | "live_trading_changed"
  | "kill_switch_changed";

export interface AuditLogRecord {
  id: string;
  event_type: AuditEventType;
  entity_type: string;
  entity_id: string;
  actor: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogRecord[];
}

export const tradeIntentEndpointExample = "POST /api/trade-intents/from-analysis/{analysis_id}";
export const riskEvaluationEndpointExample = "POST /api/trade-intents/{intent_id}/risk-evaluate";
export const orderCreateEndpointExample = "POST /api/orders";
export const orderApproveEndpointExample = "POST /api/orders/{order_id}/approve";
export const paperAccountEndpointExample = "GET /api/orders/accounts/paper";
export const automationStateEndpointExample = "GET /api/automation/state";
export const automationHealthEndpointExample = "GET /api/automation/health";
export const killSwitchEndpointExample = "POST /api/automation/kill-switch/activate";
export const liveTradingEndpointExample = "POST /api/automation/live-trading";
export const liveTradingConfirmEndpointExample = "POST /api/automation/live-trading/confirm";
export const orderSyncEndpointExample = "POST /api/orders/{order_id}/sync";
export const orderSyncAllEndpointExample = "POST /api/orders/sync/all";
export const orderCancelEndpointExample = "POST /api/orders/{order_id}/cancel";
export const orderReplaceEndpointExample = "POST /api/orders/{order_id}/replace";
export const auditEndpointExample = "GET /api/audit";
export const alpacaBrokerHealthEndpointExample = "GET /api/brokers/alpaca/health";
export const alpacaBrokerConnectTestEndpointExample = "POST /api/brokers/alpaca/connect/test";
export const alpacaPaperReadinessEndpointExample = "GET /api/brokers/alpaca/paper-readiness";
export const analysisRuntimeProfileEndpointExample = "GET /api/analysis/runtime-profile";
export const analysisRuntimeHealthEndpointExample = "GET /api/analysis/runtime-health";
export const platformPreflightEndpointExample = "GET /api/diagnostics/preflight";

export const sampleTradeIntent: TradeIntentRecord = {
  id: "intent_demo",
  analysis_id: "analysis_demo",
  symbol: "AAPL",
  trade_date: "2026-04-25",
  mode: "paper_manual",
  rating: "BUY",
  side: "buy",
  status: "approval_required",
  confidence: 0.78,
  entry_type: "market",
  time_horizon: "swing",
  max_position_pct: 0.08,
  max_loss_pct: 0.03,
  take_profit_pct: 0.09,
  thesis_summary: "Momentum, analyst alignment, and supportive fundamentals point to a tactical long setup.",
  source_signal: "BUY",
  risk_flags: ["earnings_risk"],
  risk_summary: {
    outcome: "approval_required",
    checks: [
      {
        rule_code: "mode.manual_approval",
        severity: "warning",
        outcome: "require_approval",
        message: "Manual modes require operator approval before order submission.",
      },
      {
        rule_code: "flags.elevated_event_risk",
        severity: "warning",
        outcome: "require_approval",
        message: "Elevated narrative risk flags require manual review before execution.",
      },
    ],
  },
};

export const sampleOrder: OrderRecord = {
  id: "order_demo",
  intent_id: "intent_demo",
  analysis_id: "analysis_demo",
  symbol: "AAPL",
  broker_name: "alpaca",
  broker_environment: "paper",
  side: "buy",
  order_type: "market",
  quantity: 80,
  broker_order_id: "broker-order-1",
  requested_price: 100,
  filled_price: 100,
  average_fill_price: 100,
  status: "filled",
  status_reason: "Approved by operator and filled in Alpaca paper simulator.",
  approval_required: true,
  last_synced_at: "2026-04-25T10:00:05Z",
  filled_quantity: 80,
  remaining_quantity: 0,
};

export const sampleAccountSnapshot: AccountSnapshot = {
  cash: 92000,
  equity: 100000,
  buying_power: 92000,
  positions: [
    {
      symbol: "AAPL",
      quantity: 80,
      average_price: 100,
      market_value: 8000,
    },
  ],
};

export const sampleAutomationHealth: AutomationHealthSnapshot = {
  kill_switch_active: false,
  auto_trading_enabled: true,
  effective_auto_trading_enabled: true,
  effective_live_trading_enabled: true,
  broker_sync_healthy: true,
  broker_sync_stale: false,
  consecutive_broker_failures: 0,
  status_summary: "Automation controls are healthy and auto trading is enabled.",
  state: {
    kill_switch_active: false,
    auto_trading_enabled: true,
    live_trading_enabled: true,
    live_trading_double_confirmed: true,
    live_trading_unlocked_by: "alice",
    live_trading_unlocked_at: "2026-04-25T09:59:00Z",
    broker_sync_healthy: true,
    last_broker_sync_at: "2026-04-25T10:00:00Z",
    sync_stale_after_seconds: 900,
    consecutive_broker_failures: 0,
    max_consecutive_broker_failures: 3,
    scheduler: {
      enabled: true,
      interval_minutes: 30,
      target_mode: "paper_auto",
    },
  },
};

export const sampleBrokerHealth: BrokerHealthCheckResult = {
  broker_name: "alpaca",
  environment: "paper",
  integration_mode: "api",
  configured: true,
  credentials_present: true,
  connectivity_ok: true,
  message: "Alpaca paper connectivity check succeeded.",
  base_url: "https://paper-api.alpaca.markets/v2",
  account_snapshot: sampleAccountSnapshot,
  checked_at: "2026-04-25T10:00:00Z",
};

export const sampleAlpacaPaperReadiness: AlpacaPaperReadiness = {
  broker_health: sampleBrokerHealth,
  automation_health: sampleAutomationHealth,
  manual_ready: true,
  auto_ready: true,
  checklist: [
    "Manual Alpaca paper flow is ready.",
    "Auto Alpaca paper flow is ready.",
  ],
};

export const sampleAuditLogs: AuditLogListResponse = {
  items: [
    {
      id: "audit_1",
      event_type: "order_created",
      entity_type: "order",
      entity_id: "order_demo",
      actor: "system",
      metadata: {},
      created_at: "2026-04-25T10:00:00Z",
    },
    {
      id: "audit_2",
      event_type: "order_approved",
      entity_type: "order",
      entity_id: "order_demo",
      actor: "operator",
      metadata: { note: "Manual paper approval" },
      created_at: "2026-04-25T10:00:04Z",
    },
  ],
};
