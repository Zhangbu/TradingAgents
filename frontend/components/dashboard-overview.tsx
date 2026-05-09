"use client";

import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import { formatTimestamp, formatWholeDollars } from "../lib/format";
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
  account: AccountSnapshot | null;
  orders: OrderRecord[];
  analyses: AnalysisRunRecord[];
  tradeIntents: TradeIntentRecord[];
  audit: AuditLogListResponse | null;
};

const emptyState: DashboardState = {
  readiness: null,
  preflight: null,
  account: null,
  orders: [],
  analyses: [],
  tradeIntents: [],
  audit: null,
};

export function DashboardOverview() {
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
      const [readiness, preflight, account, orderResponse, analysisResponse, tradeIntentResponse, audit] =
        await Promise.all([
          apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
          apiRequest<PlatformPreflightSummary>("/diagnostics/preflight"),
          apiRequest<AccountSnapshot>("/orders/accounts/paper?broker_name=alpaca"),
          apiRequest<{ items: OrderRecord[] }>("/orders?limit=8"),
          apiRequest<{ items: AnalysisRunRecord[] }>("/analysis/runs?limit=6"),
          apiRequest<{ items: TradeIntentRecord[] }>("/trade-intents?limit=8"),
          apiRequest<AuditLogListResponse>("/audit?limit=6"),
        ]);

      setState({
        readiness,
        preflight,
        account,
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
          label="Buying Power"
          value={formatWholeDollars(state.account?.buying_power)}
          tone="positive"
        />
        <MetricCard
          label="Open Positions"
          value={String(state.account?.positions.length ?? 0)}
        />
        <MetricCard
          label="Pending Approval"
          value={String(pendingApprovals)}
          tone={pendingApprovals > 0 ? "warning" : "neutral"}
        />
        <MetricCard
          label="Auto Flow"
          value={state.preflight?.paper_auto.ready ? "Ready" : "Paused"}
          tone={state.preflight?.paper_auto.ready ? "positive" : "warning"}
        />
      </section>

      {error ? <div className="callout callout-error">{error}</div> : null}

      <section className="grid columns-3">
        <article className="card span-2">
          <div className="section-heading">
            <div>
              <span className="eyebrow">System state</span>
              <h2>Readiness and guardrails</h2>
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
              {busy ? "Refreshing..." : "Refresh"}
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
          <h2>Operator attention</h2>
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
          <span className="eyebrow">Today's opportunities</span>
          <h2>Actionable agent calls</h2>
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
          <h2>Open orders and positions</h2>
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
          <h2>Why the system is saying no</h2>
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
          <h2>Recent completed analyses</h2>
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
        <h2>Latest system events</h2>
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
