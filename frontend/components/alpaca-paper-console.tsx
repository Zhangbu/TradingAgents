"use client";

import { startTransition, useEffect, useState } from "react";

import { apiBaseUrl, apiRequest } from "../lib/api";
import type {
  AccountSnapshot,
  AlpacaPaperReadiness,
  AnalysisRunRecord,
  AutomationHealthSnapshot,
  OrderRecord,
  TradeIntentRecord,
} from "../shared/contracts/analysis";

type FlowMode = "paper_manual" | "paper_auto";

type LaunchResult = {
  analysis?: AnalysisRunRecord;
  tradeIntent?: TradeIntentRecord;
  order?: OrderRecord;
};

const initialLaunchResult: LaunchResult = {};

export function AlpacaPaperConsole() {
  const [symbol, setSymbol] = useState("AAPL");
  const [tradeDate, setTradeDate] = useState("2026-04-26");
  const [flowMode, setFlowMode] = useState<FlowMode>("paper_manual");
  const [referencePrice, setReferencePrice] = useState("100");
  const [limitPrice, setLimitPrice] = useState("1");
  const [reviewer, setReviewer] = useState("operator");

  const [readiness, setReadiness] = useState<AlpacaPaperReadiness | null>(null);
  const [automationHealth, setAutomationHealth] =
    useState<AutomationHealthSnapshot | null>(null);
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [launchResult, setLaunchResult] =
    useState<LaunchResult>(initialLaunchResult);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  useEffect(() => {
    void refreshConsole();
  }, []);

  async function refreshConsole() {
    setBusyAction("refresh");
    setError(null);

    try {
      const [nextReadiness, nextAutomationHealth, nextAccount, nextOrders] =
        await Promise.all([
          apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
          apiRequest<AutomationHealthSnapshot>("/automation/health"),
          apiRequest<AccountSnapshot>("/orders/accounts/paper?broker_name=alpaca"),
          apiRequest<{ items: OrderRecord[] }>("/orders?limit=12"),
        ]);

      setReadiness(nextReadiness);
      setAutomationHealth(nextAutomationHealth);
      setAccount(nextAccount);
      const nextAlpacaOrders = nextOrders.items.filter((order) => order.broker_name === "alpaca");
      setOrders(nextAlpacaOrders);
      setSelectedOrderId((current) => current ?? nextAlpacaOrders[0]?.id ?? null);
      setNotice("Console refreshed from backend API.");
    } catch (refreshError) {
      setError(normalizeError(refreshError));
    } finally {
      setBusyAction(null);
    }
  }

  async function testConnectivity() {
    setBusyAction("connect");
    setError(null);
    setNotice(null);

    try {
      const nextReadiness =
        await apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness");
      await apiRequest("/brokers/alpaca/connect/test", { method: "POST" });
      setReadiness(nextReadiness);
      setNotice("Alpaca paper connectivity check succeeded.");
    } catch (connectError) {
      setError(normalizeError(connectError));
    } finally {
      setBusyAction(null);
    }
  }

  async function recordBrokerSync() {
    setBusyAction("sync-health");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/broker-sync", {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshConsole();
      setNotice("Broker sync timestamp refreshed.");
    } catch (syncError) {
      setError(normalizeError(syncError));
      setBusyAction(null);
    }
  }

  async function setAutoTrading(enabled: boolean) {
    setBusyAction(enabled ? "auto-on" : "auto-off");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/auto-trading", {
        method: "POST",
        body: JSON.stringify({ enabled }),
      });
      await refreshConsole();
      setNotice(enabled ? "Auto trading enabled." : "Auto trading disabled.");
    } catch (autoError) {
      setError(normalizeError(autoError));
      setBusyAction(null);
    }
  }

  async function launchFlow() {
    setBusyAction("launch");
    setError(null);
    setNotice(null);
    setLaunchResult(initialLaunchResult);

    try {
      const analysis = await apiRequest<AnalysisRunRecord>("/analysis/runs", {
        method: "POST",
        body: JSON.stringify({
          symbol,
          trade_date: tradeDate,
          selected_analysts: ["market", "social", "news", "fundamentals"],
          mode: flowMode,
        }),
      });

      if (analysis.status === "failed") {
        setLaunchResult({ analysis });
        setError(analysis.error_message ?? "Analysis execution failed.");
        await refreshConsole();
        return;
      }

      const tradeIntent = await apiRequest<TradeIntentRecord>(
        `/trade-intents/from-analysis/${analysis.id}`,
        { method: "POST" },
      );
      const evaluatedIntent = await apiRequest<TradeIntentRecord>(
        `/trade-intents/${tradeIntent.id}/risk-evaluate`,
        { method: "POST" },
      );

      let createdOrder: OrderRecord | undefined;
      if (evaluatedIntent.side !== "hold" && evaluatedIntent.status !== "blocked") {
        createdOrder = await apiRequest<OrderRecord>("/orders", {
          method: "POST",
          body: JSON.stringify({
            intent_id: evaluatedIntent.id,
            broker_name: "alpaca",
            broker_environment: "paper",
            reference_price: Number(referencePrice),
            limit_price: limitPrice ? Number(limitPrice) : null,
          }),
        });
      }

      setLaunchResult({
        analysis,
        tradeIntent: evaluatedIntent,
        order: createdOrder,
      });
      await refreshConsole();
      setNotice("Paper flow launched successfully.");
    } catch (launchError) {
      setError(normalizeError(launchError));
      setBusyAction(null);
    }
  }

  async function approveOrder(orderId: string) {
    setBusyAction(`approve-${orderId}`);
    setError(null);
    setNotice(null);

    try {
      const approvedOrder = await apiRequest<OrderRecord>(`/orders/${orderId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          reviewer,
          note: "Approved from Alpaca paper console.",
        }),
      });

      setLaunchResult((current) =>
        current.order?.id === orderId ? { ...current, order: approvedOrder } : current,
      );
      await refreshConsole();
      setNotice("Pending order approved and submitted to Alpaca paper.");
    } catch (approveError) {
      setError(normalizeError(approveError));
      setBusyAction(null);
    }
  }

  async function syncOrder(orderId: string) {
    setBusyAction(`sync-${orderId}`);
    setError(null);
    setNotice(null);

    try {
      await apiRequest(`/orders/${orderId}/sync`, { method: "POST" });
      await refreshConsole();
      setNotice("Order synced from Alpaca paper.");
    } catch (syncError) {
      setError(normalizeError(syncError));
      setBusyAction(null);
    }
  }

  async function cancelOrder(orderId: string) {
    setBusyAction(`cancel-${orderId}`);
    setError(null);
    setNotice(null);

    try {
      const canceledOrder = await apiRequest<OrderRecord>(`/orders/${orderId}/cancel`, {
        method: "POST",
        body: JSON.stringify({
          reviewer,
          note: "Canceled from Alpaca paper console.",
        }),
      });

      setLaunchResult((current) =>
        current.order?.id === orderId ? { ...current, order: canceledOrder } : current,
      );
      await refreshConsole();
      setNotice("Order canceled at Alpaca paper.");
    } catch (cancelError) {
      setError(normalizeError(cancelError));
      setBusyAction(null);
    }
  }

  const pendingApprovalOrder = launchResult.order?.status === "pending_approval"
    ? launchResult.order
    : orders.find((order) => order.status === "pending_approval");
  const focusOrder =
    launchResult.order ??
    orders.find((order) => order.id === selectedOrderId) ??
    orders[0] ??
    null;

  return (
    <div className="stack">
      <section className="hero hero-console">
        <div className="hero-copy">
          <span className="eyebrow">Alpaca Paper Console</span>
          <h1>Launch, approve, sync, and cancel paper trades from one desk.</h1>
          <p>
            The backend workflow is already live. This console turns it into an operator
            path you can actually use while we keep tightening the frontend.
          </p>
        </div>
        <div className="hero-actions">
          <button
            className="button"
            type="button"
            onClick={() => {
              startTransition(() => {
                void launchFlow();
              });
            }}
            disabled={busyAction !== null}
          >
            {busyAction === "launch" ? "Launching..." : "Launch paper flow"}
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => {
              startTransition(() => {
                void refreshConsole();
              });
            }}
            disabled={busyAction !== null}
          >
            {busyAction === "refresh" ? "Refreshing..." : "Refresh console"}
          </button>
        </div>
      </section>

      <section className="grid columns-3 section-tight">
        <article className="card metric-card">
          <span className="pill">Manual</span>
          <p className="metric">{readiness?.manual_ready ? "Ready" : "Blocked"}</p>
          <p>{readiness?.checklist[0] ?? "Waiting for broker readiness."}</p>
        </article>
        <article className="card metric-card">
          <span className="pill pill-accent">Auto</span>
          <p className="metric">{readiness?.auto_ready ? "Ready" : "Paused"}</p>
          <p>
            {automationHealth?.status_summary ??
              "Waiting for automation health snapshot."}
          </p>
        </article>
        <article className="card metric-card">
          <span className="pill">Account</span>
          <p className="metric">
            {account ? `$${Math.round(account.buying_power).toLocaleString()}` : "--"}
          </p>
          <p>Current Alpaca paper buying power.</p>
        </article>
      </section>

      {(error || notice) && (
        <section className="section-tight">
          {error ? <div className="callout callout-error">{error}</div> : null}
          {notice ? <div className="callout callout-success">{notice}</div> : null}
        </section>
      )}

      <section className="grid columns-2">
        <article className="card">
          <h2>Launch settings</h2>
          <div className="form-grid">
            <label className="field">
              <span>Symbol</span>
              <input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} />
            </label>
            <label className="field">
              <span>Trade date</span>
              <input value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} />
            </label>
            <label className="field">
              <span>Mode</span>
              <select value={flowMode} onChange={(event) => setFlowMode(event.target.value as FlowMode)}>
                <option value="paper_manual">paper_manual</option>
                <option value="paper_auto">paper_auto</option>
              </select>
            </label>
            <label className="field">
              <span>Reviewer</span>
              <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
            </label>
            <label className="field">
              <span>Reference price</span>
              <input value={referencePrice} onChange={(event) => setReferencePrice(event.target.value)} />
            </label>
            <label className="field">
              <span>Limit price</span>
              <input value={limitPrice} onChange={(event) => setLimitPrice(event.target.value)} />
            </label>
          </div>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void launchFlow();
                });
              }}
              disabled={busyAction !== null}
            >
              Run analysis to order
            </button>
            <a className="button-secondary" href={`${apiBaseUrl}/brokers/alpaca/paper-readiness`}>
              Open readiness JSON
            </a>
          </div>
        </article>

        <article className="card">
          <h2>Broker controls</h2>
          <div className="stack">
            <div className="status-row">
              <span>Connectivity</span>
              <strong>{readiness?.broker_health.connectivity_ok ? "Connected" : "Check required"}</strong>
            </div>
            <div className="status-row">
              <span>Integration mode</span>
              <strong>{readiness?.broker_health.integration_mode ?? "--"}</strong>
            </div>
            <div className="status-row">
              <span>Auto trading</span>
              <strong>{automationHealth?.effective_auto_trading_enabled ? "Enabled" : "Paused"}</strong>
            </div>
          </div>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void testConnectivity();
                });
              }}
              disabled={busyAction !== null}
            >
              Test Alpaca connection
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void recordBrokerSync();
                });
              }}
              disabled={busyAction !== null}
            >
              Record broker sync
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void setAutoTrading(true);
                });
              }}
              disabled={busyAction !== null}
            >
              Enable auto trading
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void setAutoTrading(false);
                });
              }}
              disabled={busyAction !== null}
            >
              Disable auto trading
            </button>
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <h2>Latest launch trace</h2>
          <div className="stack">
            <TraceItem
              label="Analysis"
              body={
                launchResult.analysis
                  ? `${launchResult.analysis.symbol} • ${launchResult.analysis.status} • ${launchResult.analysis.id}`
                  : "No new analysis yet."
              }
            />
            <TraceItem
              label="Trade intent"
              body={
                launchResult.tradeIntent
                  ? `${launchResult.tradeIntent.side} • ${launchResult.tradeIntent.status} • ${launchResult.tradeIntent.id}`
                  : "No trade intent yet."
              }
            />
            <TraceItem
              label="Order"
              body={
                launchResult.order
                  ? `${launchResult.order.status} • ${launchResult.order.broker_status_raw ?? "local"} • ${launchResult.order.id}`
                  : "No order created yet."
              }
            />
          </div>
          {pendingApprovalOrder ? (
            <div className="inline-panel">
              <strong>Pending approval</strong>
              <p>
                {pendingApprovalOrder.symbol} • {pendingApprovalOrder.order_type} •{" "}
                {pendingApprovalOrder.quantity} shares
              </p>
              <button
                className="button"
                type="button"
                onClick={() => {
                  startTransition(() => {
                    void approveOrder(pendingApprovalOrder.id);
                  });
                }}
                disabled={busyAction !== null}
              >
                {busyAction === `approve-${pendingApprovalOrder.id}`
                  ? "Approving..."
                  : "Approve pending order"}
              </button>
            </div>
          ) : null}
        </article>

        <article className="card">
          <h2>Order focus</h2>
          {focusOrder ? (
            <div className="stack">
              <div className="inline-panel">
                <strong>
                  {focusOrder.symbol} • {focusOrder.side.toUpperCase()}
                </strong>
                <p>
                  {focusOrder.status} • {focusOrder.broker_status_raw ?? "local"} •{" "}
                  {focusOrder.quantity} shares
                </p>
              </div>
              <OrderTimeline order={focusOrder} />
            </div>
          ) : (
            <p className="muted">Launch a paper flow to populate the order timeline.</p>
          )}
        </article>
      </section>

      <section className="grid columns-3">
        <article className="card span-2">
          <span className="eyebrow">Execution guidance</span>
          <h2>Manual vs auto flow notes</h2>
          <div className="stack">
            <div className="inline-panel">
              <strong>paper_manual</strong>
              <p>
                Use this when you want the analysis and risk pipeline to stop at operator
                approval. The order will be created as <code>pending_approval</code> and
                only hits Alpaca after you approve it.
              </p>
            </div>
            <div className="inline-panel">
              <strong>paper_auto</strong>
              <p>
                Use this when readiness is green and you want a clean end-to-end paper
                execution check. The order submits immediately, but still respects auto
                trading, sync health, and the kill switch.
              </p>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>Account snapshot</h2>
          {account ? (
            <div className="stack">
              <div className="status-row">
                <span>Cash</span>
                <strong>${Math.round(account.cash).toLocaleString()}</strong>
              </div>
              <div className="status-row">
                <span>Equity</span>
                <strong>${Math.round(account.equity).toLocaleString()}</strong>
              </div>
              <div className="status-row">
                <span>Buying power</span>
                <strong>${Math.round(account.buying_power).toLocaleString()}</strong>
              </div>
              <div className="inline-panel">
                <strong>Positions</strong>
                {account.positions.length === 0 ? (
                  <p>No paper positions right now.</p>
                ) : (
                  <ul className="list">
                    {account.positions.map((position) => (
                      <li key={position.symbol}>
                        {position.symbol} • {position.quantity} @ ${position.average_price}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <p className="muted">Waiting for account snapshot.</p>
          )}
        </article>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Orders</span>
            <h2>Recent Alpaca paper orders</h2>
          </div>
          <p className="muted">Use sync and cancel here while we build the fuller trading desk.</p>
        </div>
        <div className="order-table">
          {orders.length === 0 ? (
            <p className="muted">No Alpaca paper orders yet.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Status</th>
                  <th>Broker</th>
                  <th>Qty</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <button
                        className={`table-link${order.id === focusOrder?.id ? " is-active" : ""}`}
                        type="button"
                        onClick={() => setSelectedOrderId(order.id)}
                      >
                        {order.symbol}
                      </button>
                    </td>
                    <td>
                      <span className={`status-badge status-${order.status}`}>
                        {order.status}
                      </span>
                    </td>
                    <td>{order.broker_status_raw ?? "local"}</td>
                    <td>
                      {order.filled_quantity ?? 0}/{order.quantity}
                    </td>
                    <td>{formatTimestamp(order.last_synced_at ?? order.canceled_at)}</td>
                    <td>
                      <div className="table-actions">
                        <button
                          className="button-secondary button-small"
                          type="button"
                          onClick={() => {
                            startTransition(() => {
                              void syncOrder(order.id);
                            });
                          }}
                          disabled={busyAction !== null}
                        >
                          Sync
                        </button>
                        {canCancel(order.status) ? (
                          <button
                            className="button-secondary button-small"
                            type="button"
                            onClick={() => {
                              startTransition(() => {
                                void cancelOrder(order.id);
                              });
                            }}
                            disabled={busyAction !== null}
                          >
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

function TraceItem({ label, body }: { label: string; body: string }) {
  return (
    <div className="inline-panel">
      <strong>{label}</strong>
      <p>{body}</p>
    </div>
  );
}

function OrderTimeline({ order }: { order: OrderRecord }) {
  const steps = [
    {
      label: "Intent linked",
      active: true,
      detail: order.intent_id,
    },
    {
      label: "Approval",
      active: order.approval_required ? order.status !== "pending_approval" : true,
      detail: order.approval_required ? "Manual gate" : "Auto path",
    },
    {
      label: "Submitted",
      active: ["submitted", "partially_filled", "filled", "canceled"].includes(order.status),
      detail: order.submitted_at ? formatTimestamp(order.submitted_at) : "Waiting",
    },
    {
      label: "Broker sync",
      active: Boolean(order.last_synced_at),
      detail: order.last_synced_at ? formatTimestamp(order.last_synced_at) : "Not synced yet",
    },
    {
      label: "Closed",
      active: ["filled", "canceled", "failed", "rejected", "expired"].includes(order.status),
      detail:
        order.canceled_at
          ? formatTimestamp(order.canceled_at)
          : order.filled_at
            ? formatTimestamp(order.filled_at)
            : order.status,
    },
  ];

  return (
    <div className="timeline">
      {steps.map((step) => (
        <div
          key={step.label}
          className={`timeline-item${step.active ? " is-active" : ""}`}
        >
          <span className="timeline-dot" />
          <div className="timeline-copy">
            <strong>{step.label}</strong>
            <p>{step.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function normalizeError(value: unknown): string {
  if (value instanceof Error) {
    return value.message;
  }

  return "Unexpected request failure.";
}

function canCancel(status: OrderRecord["status"]): boolean {
  return [
    "pending_approval",
    "approved",
    "submitted",
    "partially_filled",
    "replace_requested",
  ].includes(status);
}

function formatTimestamp(raw: string | undefined): string {
  if (!raw) {
    return "--";
  }

  try {
    return new Date(raw).toLocaleString();
  } catch {
    return raw;
  }
}
