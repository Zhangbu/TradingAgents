// API Types matching backend schemas

export type TradeSide = 'buy' | 'sell';
export type PositionSide = 'long' | 'short';
export type ExchangeType = 'binance' | 'okx' | 'paper';
export type ProposalStatus = 'pending' | 'approved' | 'rejected' | 'executed' | 'failed' | 'cancelled';

export interface Proposal {
  id: number;
  symbol: string;
  side: TradeSide;
  quantity: number;
  confidence?: number;
  exchange: ExchangeType;
  status: ProposalStatus;
  reasoning?: string;
  market_report?: string;
  sentiment_report?: string;
  news_report?: string;
  fundamentals_report?: string;
  investment_debate?: string;
  risk_debate?: string;
  approved_at?: string;
  approved_by?: string;
  rejection_reason?: string;
  executed_at?: string;
  execution_error?: string;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: number;
  symbol: string;
  side: PositionSide;
  quantity: number;
  entry_price: number;
  current_price?: number;
  unrealized_pnl: number;
  realized_pnl: number;
  exchange: ExchangeType;
  is_open: boolean;
  opened_at: string;
  closed_at?: string;
  close_reason?: string;
  proposal_id?: number;
}

export interface TradeHistory {
  id: number;
  symbol: string;
  side: TradeSide;
  quantity: number;
  price: number;
  total_value: number;
  exchange: ExchangeType;
  realized_pnl: number;
  executed_at: string;
  position_id?: number;
  proposal_id?: number;
}

export interface AgentLog {
  id: number;
  proposal_id: number;
  agent_type: string;
  agent_name: string;
  message: string;
  reasoning?: string;
  action?: string;
  created_at: string;
}

export interface ProposalListResponse {
  proposals: Proposal[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PositionListResponse {
  positions: Position[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TradeHistoryListResponse {
  trades: TradeHistory[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PortfolioSummary {
  total_positions: number;
  total_value: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  positions_by_exchange: Record<string, number>;
  positions_by_side: Record<string, number>;
}

export interface AgentRunRequest {
  symbol: string;
  trade_date?: string;
  selected_analysts?: string[];
  exchange?: ExchangeType;
  auto_approve?: boolean;
  max_debate_rounds?: number;
  max_risk_discuss_rounds?: number;
}

export interface AgentRunResponse {
  run_id: string;
  symbol: string;
  status: string;
  message: string;
  proposal_id?: number;
}

export interface ProposalApproval {
  approved: boolean;
  rejection_reason?: string;
}

// WebSocket message types
export interface WSMessage {
  type: 'proposal_update' | 'position_update' | 'agent_event' | 'run_status' | 'kill_switch' | 'pong';
  [key: string]: unknown;
}

export interface WSAgentEvent {
  type: 'agent_event';
  run_id: string;
  event_type: 'thinking' | 'complete' | 'error';
  timestamp: string;
  data: {
    agent?: string;
    agent_name?: string;
    message?: string;
    reasoning?: string;
    action?: string;
  };
}

export interface WSRunStatus {
  type: 'run_status';
  run_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  proposal_id?: number;
  error?: string;
}