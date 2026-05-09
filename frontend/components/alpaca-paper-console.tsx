"use client";

import { startTransition, useEffect, useState } from "react";

import { apiBaseUrl, apiRequest } from "../lib/api";
import {
  formatPrice,
  formatTimestamp,
  formatWholeDollars,
  getTodayDateInputValue,
} from "../lib/format";
import { explainBrokerStatus, summarizeExecutionState } from "../lib/order-status";
import type {
  AccountSnapshot,
  AlpacaPaperReadiness,
  AnalysisRunRecord,
  AnalysisRuntimeHealth,
  AnalysisRuntimeProfile,
  AutomationHealthSnapshot,
  BrokerSyncResult,
  FailureDetails,
  OrderRecord,
  PlatformPreflightSummary,
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
  const [tradeDate, setTradeDate] = useState("");
  const [flowMode, setFlowMode] = useState<FlowMode>("paper_manual");
  const [referencePrice, setReferencePrice] = useState("100");
  const [limitPrice, setLimitPrice] = useState("1");
  const [reviewer, setReviewer] = useState("operator");

  const [readiness, setReadiness] = useState<AlpacaPaperReadiness | null>(null);
  const [automationHealth, setAutomationHealth] =
    useState<AutomationHealthSnapshot | null>(null);
  const [runtimeProfile, setRuntimeProfile] = useState<AnalysisRuntimeProfile | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<AnalysisRuntimeHealth | null>(null);
  const [preflight, setPreflight] = useState<PlatformPreflightSummary | null>(null);
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [lastSyncResult, setLastSyncResult] = useState<BrokerSyncResult | null>(null);
  const [launchResult, setLaunchResult] =
    useState<LaunchResult>(initialLaunchResult);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  useEffect(() => {
    setTradeDate(getTodayDateInputValue());
    void refreshConsole();
  }, []);

  async function refreshConsole() {
    setBusyAction("refresh");
    setError(null);

    try {
      const [
        nextReadiness,
        nextAutomationHealth,
        nextRuntimeProfile,
        nextRuntimeHealth,
        nextPreflight,
        nextAccount,
        nextOrders,
      ] =
        await Promise.all([
          apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
          apiRequest<AutomationHealthSnapshot>("/automation/health"),
          apiRequest<AnalysisRuntimeProfile>("/analysis/runtime-profile"),
          apiRequest<AnalysisRuntimeHealth>("/analysis/runtime-health"),
          apiRequest<PlatformPreflightSummary>("/diagnostics/preflight"),
          apiRequest<AccountSnapshot>("/orders/accounts/paper?broker_name=alpaca"),
          apiRequest<{ items: OrderRecord[] }>("/orders?limit=12"),
        ]);

      setReadiness(nextReadiness);
      setAutomationHealth(nextAutomationHealth);
      setRuntimeProfile(nextRuntimeProfile);
      setRuntimeHealth(nextRuntimeHealth);
      setPreflight(nextPreflight);
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
    if (!runtimeProfile) {
      setError("Analysis runtime profile has not loaded yet. Refresh the console and try again.");
      return;
    }
    const targetPreflight =
      flowMode === "paper_auto" ? preflight?.paper_auto : preflight?.paper_manual;
    if (targetPreflight && !targetPreflight.ready) {
      const blocker =
        targetPreflight.checks.find((check) => check.state === "blocked") ??
        targetPreflight.checks[0];
      setError(
        blocker?.recommended_action ??
          blocker?.message ??
          `${flowMode} preflight is blocked.`,
      );
      return;
    }

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
          llm_provider: runtimeProfile.llm_provider,
          deep_think_llm: runtimeProfile.deep_think_llm,
          quick_think_llm: runtimeProfile.quick_think_llm,
          data_vendors: runtimeProfile.data_vendors,
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
      setLastSyncResult(null);
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
      const syncResult = await apiRequest<BrokerSyncResult>(`/orders/${orderId}/sync`, {
        method: "POST",
      });
      setLastSyncResult(syncResult);
      await refreshConsole();
      setNotice(syncResult.summary_message ?? "Order synced from Alpaca paper.");
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
  const focusOrderStatusNote = focusOrder
    ? explainBrokerStatus(focusOrder.broker_status_raw, focusOrder.status)
    : null;
  const focusExecutionState = focusOrder ? summarizeExecutionState(focusOrder) : null;
  const manualChecks = preflight?.paper_manual.checks ?? [];
  const autoChecks = preflight?.paper_auto.checks ?? [];

  return (
    <div className="stack">
      <section className="hero hero-console">
        <div className="hero-copy">
          <span className="eyebrow">Alpaca Paper Console</span>
          <h1 className="hero-title-tight">Operate paper trades from one terminal.</h1>
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
            disabled={
              busyAction !== null ||
              runtimeProfile === null ||
              (flowMode === "paper_auto"
                ? preflight?.paper_auto.ready === false
                : preflight?.paper_manual.ready === false)
            }
          >
            {busyAction === "launch"
              ? "Launching..."
              : flowMode === "paper_auto" && preflight?.paper_auto.ready === false
                ? "Auto preflight blocked"
                : flowMode === "paper_manual" && preflight?.paper_manual.ready === false
                  ? "Manual preflight blocked"
                  : "Launch paper flow"}
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
            {formatWholeDollars(account?.buying_power)}
          </p>
          <p>Current Alpaca paper buying power.</p>
        </article>
      </section>

      <section className="grid columns-2 section-tight">
        <article className="card">
          <span className="eyebrow">Analysis runtime</span>
          <h2>Current provider and data source</h2>
          <div className="stack">
            <div className="status-row">
              <span>LLM provider</span>
              <strong>{runtimeProfile?.llm_provider ?? "--"}</strong>
            </div>
            <div className="status-row">
              <span>Deep model</span>
              <strong>{runtimeProfile?.deep_think_llm ?? "--"}</strong>
            </div>
            <div className="status-row">
              <span>Core stock vendor</span>
              <strong>{runtimeProfile?.data_vendors.core_stock_apis ?? "--"}</strong>
            </div>
            <div className="status-row">
              <span>News vendor</span>
              <strong>{runtimeProfile?.data_vendors.news_data ?? "--"}</strong>
            </div>
            <div className="status-row">
              <span>Fallback policy</span>
              <strong>{runtimeProfile?.vendor_fallback_policy ?? "--"}</strong>
            </div>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Runtime health</span>
          <h2>Pre-flight checks</h2>
          <div className="stack">
            <div className="inline-panel">
              <strong>LLM • {runtimeHealth?.llm.state ?? "--"}</strong>
              <p>{runtimeHealth?.llm.message ?? "Waiting for runtime health."}</p>
            </div>
            <div className="inline-panel">
              <strong>Market data • {runtimeHealth?.market_data.state ?? "--"}</strong>
              <p>{runtimeHealth?.market_data.message ?? "Waiting for runtime health."}</p>
            </div>
            <div className="inline-panel">
              <strong>
                Flow preflight •{" "}
                {flowMode === "paper_auto"
                  ? preflight?.paper_auto.state ?? "--"
                  : preflight?.paper_manual.state ?? "--"}
              </strong>
              <p>
                {flowMode === "paper_auto"
                  ? preflight?.paper_auto.ready
                    ? "paper_auto is ready to launch."
                    : "paper_auto is blocked until the failed gate is resolved."
                  : preflight?.paper_manual.ready
                    ? "paper_manual is ready to launch."
                    : "paper_manual is blocked until the failed gate is resolved."}
              </p>
            </div>
            {runtimeHealth?.market_data.recommended_action ? (
              <div className="inline-panel">
                <strong>Recommended next step</strong>
                <p>{runtimeHealth.market_data.recommended_action}</p>
              </div>
            ) : null}
          </div>
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
              <input
                type="date"
                value={tradeDate}
                onChange={(event) => setTradeDate(event.target.value)}
              />
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
          <div className="actions form-actions">
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
          <div className="actions form-actions">
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
          <span className="eyebrow">Broker observability</span>
          <h2>Live paper runtime snapshot</h2>
          <div className="stack">
            <StatusPanel
              label="Broker check"
              value={readiness?.broker_health.connectivity_ok ? "Healthy" : "Attention"}
              detail={readiness?.broker_health.message ?? "Waiting for broker diagnostics."}
            />
            <StatusPanel
              label="Checked at"
              value={formatTimestamp(readiness?.broker_health.checked_at)}
              detail={`Base URL • ${readiness?.broker_health.base_url ?? "--"}`}
            />
            <StatusPanel
              label="Last broker sync"
              value={formatTimestamp(automationHealth?.state.last_broker_sync_at)}
              detail={
                automationHealth?.broker_sync_stale
                  ? "The broker snapshot is stale, so automation remains cautious."
                  : automationHealth?.broker_sync_healthy
                    ? "The broker snapshot is fresh enough for guarded execution."
                    : "Broker sync is currently unhealthy."
              }
            />
            <StatusPanel
              label="Execution path"
              value={readiness?.broker_health.integration_mode ?? "--"}
              detail={
                readiness?.broker_health.integration_mode === "api"
                  ? "Orders flow to Alpaca paper over the remote API."
                  : "Orders are currently handled by the local simulator path."
              }
            />
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Flow suitability</span>
          <h2>Manual and auto gates</h2>
          <div className="stack">
            <FlowSuitability
              title="paper_manual"
              ready={Boolean(preflight?.paper_manual.ready)}
              state={preflight?.paper_manual.state ?? "--"}
              checks={manualChecks}
            />
            <FlowSuitability
              title="paper_auto"
              ready={Boolean(preflight?.paper_auto.ready)}
              state={preflight?.paper_auto.state ?? "--"}
              checks={autoChecks}
            />
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <h2>Latest launch trace</h2>
          <div className="phase-grid">
            <PhaseCard
              label="Analysis"
              state={launchResult.analysis ? launchResult.analysis.status : "idle"}
              detail={
                launchResult.analysis
                  ? `${launchResult.analysis.symbol} • ${launchResult.analysis.id}`
                  : "No new analysis yet."
              }
            />
            <PhaseCard
              label="Trade intent"
              state={launchResult.tradeIntent ? launchResult.tradeIntent.status : "idle"}
              detail={
                launchResult.tradeIntent
                  ? `${launchResult.tradeIntent.side} • ${launchResult.tradeIntent.id}`
                  : "No trade intent yet."
              }
            />
            <PhaseCard
              label="Order"
              state={launchResult.order ? launchResult.order.status : "idle"}
              detail={
                launchResult.order
                  ? `${launchResult.order.broker_status_raw ?? "local"} • ${launchResult.order.id}`
                  : "No order created yet."
              }
            />
            <PhaseCard
              label="Reconciliation"
              state={
                lastSyncResult
                  ? lastSyncResult.requires_operator_review
                    ? "review_required"
                    : "synced"
                  : "idle"
              }
              detail={
                lastSyncResult
                  ? lastSyncResult.summary_message ?? "sync completed"
                  : "No sync result captured yet."
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
              {focusOrderStatusNote ? (
                <div className="inline-panel">
                  <strong>Broker status note • {focusOrderStatusNote.label}</strong>
                  <p>{focusOrderStatusNote.meaning}</p>
                  {focusOrderStatusNote.marketHint ? (
                    <p>{focusOrderStatusNote.marketHint}</p>
                  ) : null}
                </div>
              ) : null}
              {focusExecutionState ? (
                <div className={`inline-panel execution-state execution-${focusExecutionState.tone}`}>
                  <strong>{focusExecutionState.label}</strong>
                  <p>{focusExecutionState.detail}</p>
                </div>
              ) : null}
              <OrderTimeline
                order={focusOrder}
                analysis={launchResult.analysis?.id === focusOrder.analysis_id ? launchResult.analysis : null}
                tradeIntent={launchResult.tradeIntent?.analysis_id === focusOrder.analysis_id ? launchResult.tradeIntent : null}
                syncResult={lastSyncResult}
              />
              <FailureCallout failure={focusOrder.failure_details} />
              {lastSyncResult ? (
                <div className="inline-panel">
                  <strong>Reconciliation snapshot</strong>
                  <p>{lastSyncResult.summary_message ?? "Sync completed."}</p>
                  {lastSyncResult.requires_operator_review ? (
                    <p>
                      Unmatched local: {formatSymbolList(lastSyncResult.unmatched_local_symbols)} •
                      unmatched broker: {formatSymbolList(lastSyncResult.unmatched_broker_symbols)}
                    </p>
                  ) : null}
                  <FailureCallout failure={lastSyncResult.failure_details} compact />
                </div>
              ) : null}
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
                <strong>{formatWholeDollars(account.cash)}</strong>
              </div>
              <div className="status-row">
                <span>Equity</span>
                <strong>{formatWholeDollars(account.equity)}</strong>
              </div>
              <div className="status-row">
                <span>Buying power</span>
                <strong>{formatWholeDollars(account.buying_power)}</strong>
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
                      <div className="stack status-stack">
                        <span className={`status-badge status-${order.status}`}>
                          {order.status}
                        </span>
                        <span
                          className={`status-note status-note-${summarizeExecutionState(order).tone}`}
                        >
                          {summarizeExecutionState(order).label}
                        </span>
                      </div>
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

function PhaseCard({
  label,
  state,
  detail,
}: {
  label: string;
  state: string;
  detail: string;
}) {
  const tone = getPhaseTone(state);

  return (
    <div className={`inline-panel phase-card phase-${tone}`}>
      <strong>{label}</strong>
      <p className="phase-state">{state}</p>
      <p>{detail}</p>
    </div>
  );
}

function StatusPanel({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="inline-panel">
      <strong>{label}</strong>
      <p>{value}</p>
      <p>{detail}</p>
    </div>
  );
}

function FlowSuitability({
  title,
  ready,
  state,
  checks,
}: {
  title: string;
  ready: boolean;
  state: string;
  checks: PlatformPreflightSummary["analysis"]["checks"];
}) {
  const blockers = checks.filter((check) => check.state === "blocked");
  const warnings = checks.filter((check) => check.state === "warning");
  const topIssue = blockers[0] ?? warnings[0] ?? null;

  return (
    <div className="inline-panel">
      <strong>
        {title} • {ready ? "ready" : state}
      </strong>
      <p>
        blockers {blockers.length} • warnings {warnings.length}
      </p>
      <p>
        {topIssue
          ? topIssue.recommended_action ?? topIssue.message
          : "All workflow gates currently look healthy."}
      </p>
    </div>
  );
}

function getPhaseTone(state: string): "idle" | "active" | "failed" | "complete" {
  if (["failed", "blocked", "rejected", "review_required"].includes(state)) {
    return "failed";
  }
  if (["completed", "filled", "synced", "ready", "approval_required"].includes(state)) {
    return "complete";
  }
  if (["running", "submitted", "partially_filled", "pending_approval"].includes(state)) {
    return "active";
  }
  return "idle";
}

function OrderTimeline({
  order,
  analysis,
  tradeIntent,
  syncResult,
}: {
  order: OrderRecord;
  analysis: AnalysisRunRecord | null;
  tradeIntent: TradeIntentRecord | null;
  syncResult: BrokerSyncResult | null;
}) {
  const executionState = summarizeExecutionState(order);
  const steps = [
    {
      label: "Analysis",
      active: analysis !== null,
      detail:
        analysis === null
          ? "No linked analysis loaded"
          : analysis.failure_details
            ? analysis.failure_details.code
            : `${analysis.status} • ${analysis.llm_provider ?? "default"}`,
      tone: analysis?.status === "failed" ? "failed" : analysis ? "active" : "idle",
    },
    {
      label: "Trade intent",
      active: tradeIntent !== null,
      detail:
        tradeIntent === null
          ? order.intent_id
          : `${tradeIntent.side} • ${tradeIntent.status} • confidence ${Math.round(
              tradeIntent.confidence * 100,
            )}%`,
      tone:
        tradeIntent?.status === "blocked"
          ? "failed"
          : tradeIntent
            ? "active"
            : "idle",
    },
    {
      label: "Approval",
      active: order.approval_required ? order.status !== "pending_approval" : true,
      detail: order.approval_required ? "Manual gate" : "Auto path",
      tone: order.status === "rejected" ? "failed" : order.approval_required ? "active" : "idle",
    },
    {
      label: "Order submission",
      active: ["submitted", "partially_filled", "filled", "canceled", "failed"].includes(order.status),
      detail: order.submitted_at ? formatTimestamp(order.submitted_at) : "Waiting",
      tone: order.status === "failed" ? "failed" : order.submitted_at ? "active" : "idle",
    },
    {
      label: "Market execution",
      active: Boolean(order.broker_status_raw) || executionState.tone !== "active",
      detail: `${executionState.label} • ${order.broker_status_raw ?? order.status}`,
      tone:
        executionState.tone === "failed"
          ? "failed"
          : executionState.tone === "waiting"
            ? "idle"
            : "active",
    },
    {
      label: "Broker sync",
      active: Boolean(order.last_synced_at) || syncResult !== null,
      detail:
        syncResult?.summary_message ??
        (order.last_synced_at ? formatTimestamp(order.last_synced_at) : "Not synced yet"),
      tone:
        syncResult?.failure_details || order.failure_details
          ? "failed"
          : order.last_synced_at || syncResult
            ? "active"
            : "idle",
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
      tone:
        ["failed", "rejected", "expired"].includes(order.status)
          ? "failed"
          : ["filled", "canceled"].includes(order.status)
            ? "active"
            : "idle",
    },
  ];

  return (
    <div className="timeline">
      {steps.map((step) => (
        <div
          key={step.label}
          className={`timeline-item${step.active ? " is-active" : ""}${
            step.tone === "failed" ? " is-failed" : ""
          }`}
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

function FailureCallout({
  failure,
  compact = false,
}: {
  failure?: FailureDetails | null;
  compact?: boolean;
}) {
  if (!failure) {
    return null;
  }

  return (
    <div className="callout callout-error">
      <strong>
        {failure.code} • {failure.component}
      </strong>
      <p>{failure.message}</p>
      {!compact ? (
        <>
          <p>
            {failure.retryable ? "Retryable" : "Needs operator fix"} • {failure.category}
          </p>
          {failure.recommended_action ? <p>{failure.recommended_action}</p> : null}
        </>
      ) : null}
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

function formatSymbolList(symbols: string[]): string {
  if (symbols.length === 0) {
    return "none";
  }

  return symbols.join(", ");
}
