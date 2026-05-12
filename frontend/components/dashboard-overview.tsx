"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import { formatTimestamp, formatWholeDollars } from "../lib/format";
import { useUiLanguage } from "../shared/ui-language";
import type {
  AccountSnapshot,
  AlpacaPaperReadiness,
  AnalysisRunRecord,
  AuditLogListResponse,
  OrderRecord,
  PlatformPreflightSummary,
  TradeIntentRecord,
} from "../shared/contracts/analysis";

type DashboardState = {
  readiness: AlpacaPaperReadiness | null;
  preflight: PlatformPreflightSummary | null;
  alpacaAccount: AccountSnapshot | null;
  ibAccount: AccountSnapshot | null;
  orders: OrderRecord[];
  analyses: AnalysisRunRecord[];
  tradeIntents: TradeIntentRecord[];
  audit: AuditLogListResponse | null;
};

const emptyState: DashboardState = {
  readiness: null,
  preflight: null,
  alpacaAccount: null,
  ibAccount: null,
  orders: [],
  analyses: [],
  tradeIntents: [],
  audit: null,
};

export function DashboardOverview() {
  const { text } = useUiLanguage();
  const [state, setState] = useState<DashboardState>(emptyState);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setBusy(true);
    setError(null);

    try {
      const [readiness, preflight, alpacaAccount, ibAccount, orderResponse, analysisResponse, tradeIntentResponse, audit] =
        await Promise.all([
          apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
          apiRequest<PlatformPreflightSummary>("/diagnostics/preflight"),
          apiRequest<AccountSnapshot>("/orders/accounts/paper?broker_name=alpaca"),
          apiRequest<AccountSnapshot>("/orders/accounts/paper?broker_name=interactive_brokers"),
          apiRequest<{ items: OrderRecord[] }>("/orders?limit=8"),
          apiRequest<{ items: AnalysisRunRecord[] }>("/analysis/runs?limit=6"),
          apiRequest<{ items: TradeIntentRecord[] }>("/trade-intents?limit=8"),
          apiRequest<AuditLogListResponse>("/audit?limit=6"),
        ]);

      setState({
        readiness,
        preflight,
        alpacaAccount,
        ibAccount,
        orders: orderResponse.items,
        analyses: analysisResponse.items,
        tradeIntents: tradeIntentResponse.items,
        audit,
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Dashboard load failed.");
    } finally {
      setBusy(false);
    }
  }

  const totalBuyingPower =
    (state.alpacaAccount?.buying_power ?? 0) + (state.ibAccount?.buying_power ?? 0);
  const totalPositions =
    (state.alpacaAccount?.positions.length ?? 0) + (state.ibAccount?.positions.length ?? 0);
  const pendingApprovals = state.orders.filter(
    (order) => order.status === "pending_approval",
  ).length;
  const openOrders = state.orders.filter((order) =>
    ["submitted", "approved", "partially_filled"].includes(order.status),
  );
  const actionableIntents = state.tradeIntents.filter((intent) =>
    ["ready", "approval_required"].includes(intent.status),
  );
  const blockedIntents = state.tradeIntents.filter((intent) => intent.status === "blocked");

  return (
    <div className="stack">
      <section className="grid columns-4 dashboard-grid">
        <MetricCard
          label={text({ en: "Buying Power", zh: "可用购买力" })}
          value={formatWholeDollars(totalBuyingPower)}
          tone="positive"
        />
        <MetricCard
          label={text({ en: "Open Positions", zh: "当前持仓" })}
          value={String(totalPositions)}
        />
        <MetricCard
          label={text({ en: "Pending Approval", zh: "待审批" })}
          value={String(pendingApprovals)}
          tone={pendingApprovals > 0 ? "warning" : "neutral"}
        />
        <MetricCard
          label={text({ en: "Auto Flow", zh: "自动流程" })}
          value={state.preflight?.paper_auto.ready ? text({ en: "Ready", zh: "可用" }) : text({ en: "Paused", zh: "暂停" })}
          tone={state.preflight?.paper_auto.ready ? "positive" : "warning"}
        />
      </section>

      {error ? <div className="callout callout-error">{error}</div> : null}

      <section className="grid columns-3">
        <article className="card span-2">
          <div className="section-heading">
            <div>
              <span className="eyebrow">System state</span>
              <h2>{text({ en: "Readiness and guardrails", zh: "系统状态与保护" })}</h2>
            </div>
            <button
              className="button-secondary button-small"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void refresh();
                });
              }}
              disabled={busy}
            >
              {busy ? text({ en: "Refreshing...", zh: "刷新中..." }) : text({ en: "Refresh", zh: "刷新" })}
            </button>
          </div>
          <div className="stack">
            <StatusLine
              label="Manual paper flow"
              value={state.preflight?.paper_manual.ready ? "Ready" : "Blocked"}
            />
            <StatusLine
              label="Auto paper flow"
              value={state.preflight?.paper_auto.ready ? "Ready" : "Paused"}
            />
            <StatusLine
              label="Analysis preflight"
              value={state.preflight?.analysis.ready ? "Ready" : "Blocked"}
            />
            <StatusLine
              label="Broker connectivity"
              value={state.readiness?.broker_health.connectivity_ok ? "Connected" : "Offline"}
            />
            <StatusLine
              label="Automation summary"
              value={state.readiness?.automation_health.status_summary ?? "--"}
              multiline
            />
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Checklist</span>
          <h2>{text({ en: "Operator attention", zh: "当前关注项" })}</h2>
          <ul className="list">
            {(
              state.preflight
                ? collectAttentionItems(state.preflight)
                : ["Waiting for readiness data."]
            ).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Broker accounts</span>
              <h2>{text({ en: "Paper cash and buying power", zh: "模拟盘现金与购买力" })}</h2>
            </div>
            <Link href="/paper" className="button-secondary button-small">
              {text({ en: "Open Paper", zh: "打开模拟盘" })}
            </Link>
          </div>
          <div className="stack">
            <BrokerAccountPanel
              title="Alpaca paper"
              account={state.alpacaAccount}
              note={
                state.readiness?.automation_health.state.last_broker_sync_at
                  ? `Last sync ${formatTimestamp(state.readiness.automation_health.state.last_broker_sync_at)}`
                  : "Waiting for broker sync."
              }
            />
            <BrokerAccountPanel
              title="IBKR paper"
              account={state.ibAccount}
              note="Simulator snapshot available for quick portfolio checks."
            />
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Open exposure</span>
          <h2>{text({ en: "Current positions by broker", zh: "按券商查看当前持仓" })}</h2>
          <div className="stack">
            <PositionPanel title="Alpaca paper" account={state.alpacaAccount} />
            <PositionPanel title="IBKR paper" account={state.ibAccount} />
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Today's opportunities</span>
          <h2>{text({ en: "Actionable agent calls", zh: "可操作机会" })}</h2>
          <div className="stack">
            {actionableIntents.length === 0 ? (
              <p className="muted">No actionable trade intents right now.</p>
            ) : (
              actionableIntents.map((intent) => (
                <div key={intent.id} className="inline-panel">
                  <strong>
                    {intent.symbol} • {intent.side.toUpperCase()}
                  </strong>
                  <p>
                    {intent.status} • confidence {Math.round(intent.confidence * 100)}%
                  </p>
                  <p>{intent.thesis_summary}</p>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Live queue</span>
          <h2>{text({ en: "Open orders and positions", zh: "开放订单与持仓" })}</h2>
          <div className="stack">
            {openOrders.length === 0 ? (
              <p className="muted">No open orders at the moment.</p>
            ) : (
              openOrders.map((order) => (
                <div key={order.id} className="inline-panel">
                  <strong>
                    {order.symbol} • {order.side.toUpperCase()}
                  </strong>
                  <p>
                    {order.status} • {order.filled_quantity ?? 0}/{order.quantity}
                  </p>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Risk blockade</span>
          <h2>{text({ en: "Why the system is saying no", zh: "系统为何拦截" })}</h2>
          <div className="stack">
            {blockedIntents.length === 0 ? (
              <p className="muted">No blocked trade intents at the moment.</p>
            ) : (
              blockedIntents.map((intent) => (
                <div key={intent.id} className="inline-panel">
                  <strong>{intent.symbol}</strong>
                  <p>{intent.risk_flags.join(", ") || "Blocked by deterministic policy."}</p>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Agent activity</span>
          <h2>{text({ en: "Recent completed analyses", zh: "最近完成的分析" })}</h2>
          <div className="stack">
            {state.analyses.length === 0 ? (
              <p className="muted">No saved analysis runs yet.</p>
            ) : (
              state.analyses.map((analysis) => (
                <div key={analysis.id} className="inline-panel">
                  <strong>{analysis.symbol}</strong>
                  <p>
                    {analysis.mode} • {analysis.status}
                  </p>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="card">
        <span className="eyebrow">Audit pulse</span>
        <h2>{text({ en: "Latest system events", zh: "最新系统事件" })}</h2>
        <div className="stack">
          {state.audit?.items.length ? (
            state.audit.items.map((item) => (
              <div key={item.id} className="inline-panel">
                <strong>{item.event_type}</strong>
                <p>
                  {item.entity_type} • {item.entity_id} • {formatTimestamp(item.created_at)}
                </p>
              </div>
            ))
          ) : (
            <p className="muted">No audit events yet.</p>
          )}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "warning";
}) {
  return (
    <article className={`card metric-card metric-${tone}`}>
      <span className="eyebrow">{label}</span>
      <p className="metric">{value}</p>
    </article>
  );
}

function BrokerAccountPanel({
  title,
  account,
  note,
}: {
  title: string;
  account: AccountSnapshot | null;
  note: string;
}) {
  return (
    <div className="inline-panel">
      <strong>{title}</strong>
      {account ? (
        <>
          <p>
            cash {formatWholeDollars(account.cash)} • equity {formatWholeDollars(account.equity)}
          </p>
          <p>
            buying power {formatWholeDollars(account.buying_power)} • positions {account.positions.length}
          </p>
          <p>{note}</p>
        </>
      ) : (
        <p className="muted">Account snapshot not loaded.</p>
      )}
    </div>
  );
}

function PositionPanel({
  title,
  account,
}: {
  title: string;
  account: AccountSnapshot | null;
}) {
  return (
    <div className="inline-panel">
      <strong>{title}</strong>
      {!account || account.positions.length === 0 ? (
        <p className="muted">No open positions right now.</p>
      ) : (
        <ul className="list">
          {account.positions.slice(0, 4).map((position) => (
            <li key={`${title}-${position.symbol}`}>
              {position.symbol} • {position.quantity} • {formatWholeDollars(position.market_value)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusLine({
  label,
  value,
  multiline = false,
}: {
  label: string;
  value: string;
  multiline?: boolean;
}) {
  return (
    <div className={`status-row${multiline ? " status-row-multiline" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function collectAttentionItems(preflight: PlatformPreflightSummary): string[] {
  const items = [
    ...preflight.analysis.checks,
    ...preflight.paper_manual.checks,
    ...preflight.paper_auto.checks,
  ]
    .filter((check) => check.state !== "healthy")
    .map(
      (check) =>
        `${check.component}: ${check.recommended_action ?? check.message}`,
    );

  return items.length > 0 ? Array.from(new Set(items)) : ["All preflight checks are healthy."];
}
