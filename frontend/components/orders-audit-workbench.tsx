"use client";

import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import { formatPrice, formatTimestamp } from "../lib/format";
import {
  buildBrokerTimeline,
  explainBrokerStatus,
  recommendNextPaperAction,
  summarizeExecutionState,
} from "../lib/order-status";
import type {
  AnalysisRunRecord,
  AuditLogListResponse,
  AuditLogRecord,
  FailureDetails,
  OrderRecord,
} from "../shared/contracts/analysis";

export function OrdersAuditWorkbench() {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisRunRecord | null>(null);
  const [selectedAudit, setSelectedAudit] = useState<AuditLogRecord[]>([]);
  const [busy, setBusy] = useState(false);
  const [detailBusy, setDetailBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [brokerFilter, setBrokerFilter] = useState("all");
  const [executionFilter, setExecutionFilter] = useState("all");
  const [attentionOnly, setAttentionOnly] = useState(false);

  useEffect(() => {
    void refresh();
  }, []);

  const filteredOrders = orders.filter((order) => {
    const symbolMatches =
      symbolFilter.trim().length === 0 ||
      order.symbol.toLowerCase().includes(symbolFilter.trim().toLowerCase());
    const statusMatches = statusFilter === "all" || order.status === statusFilter;
    const brokerMatches = brokerFilter === "all" || order.broker_name === brokerFilter;
    const executionMatches =
      executionFilter === "all" ||
      summarizeExecutionState(order).label.toLowerCase() === executionFilter;
    const attentionMatches =
      !attentionOnly ||
      order.status === "failed" ||
      order.status === "pending_approval" ||
      Boolean(order.failure_details);
    return symbolMatches && statusMatches && brokerMatches && executionMatches && attentionMatches;
  });

  const selectedOrder =
    filteredOrders.find((order) => order.id === selectedOrderId) ??
    orders.find((order) => order.id === selectedOrderId) ??
    null;
  const selectedOrderStatusNote = selectedOrder
    ? explainBrokerStatus(selectedOrder.broker_status_raw, selectedOrder.status)
    : null;
  const selectedExecutionState = selectedOrder
    ? summarizeExecutionState(selectedOrder)
    : null;
  const selectedNextAction = recommendNextPaperAction(selectedOrder);
  const brokerTimeline = buildBrokerTimeline(selectedOrder, selectedAudit);
  const reconciliationEvents = selectedAudit.filter(
    (item) => item.event_type === "broker_synced" || item.event_type === "reconciliation_completed",
  );

  useEffect(() => {
    if (!selectedOrder) {
      setSelectedAnalysis(null);
      setSelectedAudit([]);
      return;
    }

    void loadSelectedDetail(selectedOrder);
  }, [selectedOrderId, orders]);

  async function refresh() {
    setBusy(true);
    setError(null);

    try {
      const orderResponse = await apiRequest<{ items: OrderRecord[] }>("/orders?limit=40");
      setOrders(orderResponse.items);
      setSelectedOrderId((current) => current ?? orderResponse.items[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Workbench load failed.");
    } finally {
      setBusy(false);
    }
  }

  async function loadSelectedDetail(order: OrderRecord) {
    setDetailBusy(true);
    setDetailError(null);

    try {
      const [analysisResponse, auditResponse] = await Promise.all([
        apiRequest<AnalysisRunRecord>(`/analysis/runs/${encodeURIComponent(order.analysis_id)}`),
        apiRequest<AuditLogListResponse>(
          `/audit?entity_type=order&entity_id=${encodeURIComponent(order.id)}&limit=40`,
        ),
      ]);

      setSelectedAnalysis(analysisResponse);
      setSelectedAudit(auditResponse.items);
    } catch (loadError) {
      setDetailError(
        loadError instanceof Error ? loadError.message : "Failed to load order detail.",
      );
    } finally {
      setDetailBusy(false);
    }
  }

  return (
    <div className="grid columns-2">
      <section className="card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Orders</span>
            <h2>Execution history</h2>
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
        {error ? <div className="callout callout-error">{error}</div> : null}
        <div className="form-grid section-tight">
          <label className="field">
            <span>Filter symbol</span>
            <input
              value={symbolFilter}
              onChange={(event) => setSymbolFilter(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Status</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="pending_approval">pending_approval</option>
              <option value="approved">approved</option>
              <option value="submitted">submitted</option>
              <option value="partially_filled">partially_filled</option>
              <option value="filled">filled</option>
              <option value="canceled">canceled</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label className="field">
            <span>Broker</span>
            <select
              value={brokerFilter}
              onChange={(event) => setBrokerFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="alpaca">alpaca</option>
              <option value="interactive_brokers">interactive_brokers</option>
            </select>
          </label>
          <label className="field">
            <span>Execution</span>
            <select
              value={executionFilter}
              onChange={(event) => setExecutionFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="waiting for market">waiting for market</option>
              <option value="in progress">in progress</option>
              <option value="closed">closed</option>
              <option value="execution issue">execution issue</option>
            </select>
          </label>
          <label className="field field-checkbox">
            <span>Needs attention</span>
            <input
              type="checkbox"
              checked={attentionOnly}
              onChange={(event) => setAttentionOnly(event.target.checked)}
            />
          </label>
        </div>
        <div className="order-table">
          <table className="table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Status</th>
                <th>Execution</th>
                <th>Broker</th>
                <th>Qty</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((order) => (
                <tr
                  key={order.id}
                  className={order.id === selectedOrderId ? "table-row-selected" : ""}
                  onClick={() => setSelectedOrderId(order.id)}
                >
                  <td>
                    <div>
                      <strong>{order.symbol}</strong>
                      <div className="muted">{order.side.toUpperCase()}</div>
                    </div>
                  </td>
                  <td>
                    <div className="stack status-stack">
                      <span className={`status-badge status-${order.status}`}>{order.status}</span>
                      <span
                        className={`status-note status-note-${summarizeExecutionState(order).tone}`}
                      >
                        {summarizeExecutionState(order).label}
                      </span>
                    </div>
                  </td>
                  <td>{summarizeExecutionState(order).detail}</td>
                  <td>{order.broker_name}</td>
                  <td>
                    {order.filled_quantity ?? 0}/{order.quantity}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <span className="eyebrow">Detail</span>
        <h2>Selected order trail</h2>
        {detailError ? <div className="callout callout-error">{detailError}</div> : null}
        {selectedOrder ? (
          <div className="stack">
            <div className="inline-panel">
              <strong>
                {selectedOrder.symbol} • {selectedOrder.side.toUpperCase()} •{" "}
                {selectedOrder.status}
              </strong>
              <p>
                {selectedOrder.broker_name} • {selectedOrder.broker_environment} • raw{" "}
                {selectedOrder.broker_status_raw ?? "local"}
              </p>
            </div>

            <div className="inline-panel">
              <strong>Execution snapshot</strong>
              <p>
                Qty {selectedOrder.filled_quantity ?? 0}/{selectedOrder.quantity} •
                requested {formatPrice(selectedOrder.requested_price)} • avg fill{" "}
                {formatPrice(selectedOrder.average_fill_price ?? selectedOrder.filled_price)}
              </p>
              <p>
                Created {formatTimestamp(selectedOrder.created_at)} • Submitted{" "}
                {formatTimestamp(selectedOrder.submitted_at)} • Synced{" "}
                {formatTimestamp(selectedOrder.last_synced_at)}
              </p>
              {selectedOrder.status_reason ? <p>{selectedOrder.status_reason}</p> : null}
            </div>

            {selectedOrderStatusNote ? (
              <div className="inline-panel">
                <strong>Broker status note • {selectedOrderStatusNote.label}</strong>
                <p>{selectedOrderStatusNote.meaning}</p>
                {selectedOrderStatusNote.marketHint ? (
                  <p>{selectedOrderStatusNote.marketHint}</p>
                ) : null}
              </div>
            ) : null}

            {selectedExecutionState ? (
              <div className={`inline-panel execution-state execution-${selectedExecutionState.tone}`}>
                <strong>{selectedExecutionState.label}</strong>
                <p>{selectedExecutionState.detail}</p>
              </div>
            ) : null}

            <div className="inline-panel">
              <strong>Next action</strong>
              <p>{selectedNextAction.label}</p>
              <p>{selectedNextAction.detail}</p>
            </div>

            <div className="timeline-card">
              <strong>Broker timeline</strong>
              <div className="timeline-list">
                {brokerTimeline.map((event) => (
                  <div key={event.label} className={`timeline-entry timeline-${event.state}`}>
                    <div className="timeline-marker" />
                    <div className="timeline-body">
                      <div className="timeline-heading">
                        <strong>{event.label}</strong>
                        <span>{formatTimestamp(event.timestamp)}</span>
                      </div>
                      <p>{event.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <FailurePanel failure={selectedOrder.failure_details} />

            <div className="inline-panel">
              <strong>Related analysis</strong>
              {detailBusy ? (
                <p className="muted">Loading analysis context...</p>
              ) : selectedAnalysis ? (
                <>
                  <p>
                    {selectedAnalysis.status} • provider {selectedAnalysis.llm_provider ?? "default"}{" "}
                    • vendor {selectedAnalysis.data_vendors?.core_stock_apis ?? "default"}
                  </p>
                  {selectedAnalysis.failure_details ? (
                    <FailurePanel failure={selectedAnalysis.failure_details} condensed />
                  ) : selectedAnalysis.artifacts?.final_trade_decision ? (
                    <p>{selectedAnalysis.artifacts.final_trade_decision}</p>
                  ) : (
                    <p className="muted">No final trade decision artifact recorded.</p>
                  )}
                </>
              ) : (
                <p className="muted">No linked analysis record loaded.</p>
              )}
            </div>

            <div className="inline-panel">
              <strong>Audit timeline</strong>
              {detailBusy ? (
                <p className="muted">Loading audit trail...</p>
              ) : selectedAudit.length === 0 ? (
                <p className="muted">No audit events recorded for this order yet.</p>
              ) : (
                <div className="stack">
                  {selectedAudit.map((item) => (
                    <div key={item.id} className="inline-panel">
                      <strong>{item.event_type}</strong>
                      <p>
                        {item.actor} • {formatTimestamp(item.created_at)}
                      </p>
                      {Object.keys(item.metadata ?? {}).length > 0 ? (
                        <p className="muted">{formatMetadata(item.metadata)}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="inline-panel">
              <strong>Reconciliation trail</strong>
              {detailBusy ? (
                <p className="muted">Loading reconciliation events...</p>
              ) : reconciliationEvents.length === 0 ? (
                <p className="muted">No broker sync or reconciliation events recorded yet.</p>
              ) : (
                <div className="stack">
                  {reconciliationEvents.map((item) => (
                    <div key={item.id} className="inline-panel">
                      <strong>{item.event_type}</strong>
                      <p>{formatTimestamp(item.created_at)}</p>
                      <p className="muted">{formatMetadata(item.metadata)}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="muted">Choose an order to inspect its execution and audit trail.</p>
        )}
      </section>
    </div>
  );
}

function FailurePanel({
  failure,
  condensed = false,
}: {
  failure?: FailureDetails | null;
  condensed?: boolean;
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
      {!condensed ? (
        <>
          <p>
            Category {failure.category} • {failure.retryable ? "retryable" : "operator fix required"}
          </p>
          {failure.recommended_action ? <p>{failure.recommended_action}</p> : null}
        </>
      ) : null}
    </div>
  );
}

function formatMetadata(metadata: Record<string, unknown>): string {
  return Object.entries(metadata)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(" • ");
}
