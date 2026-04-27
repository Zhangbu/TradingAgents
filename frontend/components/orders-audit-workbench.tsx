"use client";

import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import type {
  AuditLogListResponse,
  OrderRecord,
} from "../shared/contracts/analysis";

export function OrdersAuditWorkbench() {
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [audit, setAudit] = useState<AuditLogListResponse | null>(null);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [symbolFilter, setSymbolFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setBusy(true);
    setError(null);

    try {
      const [orderResponse, auditResponse] = await Promise.all([
        apiRequest<{ items: OrderRecord[] }>("/orders?limit=24"),
        apiRequest<AuditLogListResponse>("/audit?limit=30"),
      ]);

      setOrders(orderResponse.items);
      setAudit(auditResponse);
      setSelectedOrderId((current) => current ?? orderResponse.items[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Workbench load failed.");
    } finally {
      setBusy(false);
    }
  }

  const selectedOrder = orders.find((order) => order.id === selectedOrderId) ?? null;
  const filteredOrders = orders.filter((order) => {
    const symbolMatches =
      symbolFilter.trim().length === 0 ||
      order.symbol.toLowerCase().includes(symbolFilter.trim().toLowerCase());
    const statusMatches = statusFilter === "all" || order.status === statusFilter;
    return symbolMatches && statusMatches;
  });
  const relatedAudit = selectedOrder
    ? (audit?.items ?? []).filter(
        (item) => item.entity_type === "order" && item.entity_id === selectedOrder.id,
      )
    : audit?.items ?? [];

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
        </div>
        <div className="order-table">
          <table className="table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Status</th>
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
                  <td>{order.symbol}</td>
                  <td>{order.status}</td>
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
        <span className="eyebrow">Audit</span>
        <h2>Selected order trail</h2>
        {selectedOrder ? (
          <div className="stack">
            <div className="inline-panel">
              <strong>
                {selectedOrder.symbol} • {selectedOrder.side.toUpperCase()}
              </strong>
              <p>
                {selectedOrder.status} • {selectedOrder.broker_status_raw ?? "local"} •{" "}
                {selectedOrder.broker_environment}
              </p>
            </div>
            {relatedAudit.length === 0 ? (
              <p className="muted">No audit events recorded for this order yet.</p>
            ) : (
              relatedAudit.map((item) => (
                <div key={item.id} className="inline-panel">
                  <strong>{item.event_type}</strong>
                  <p>
                    {item.actor} • {formatTimestamp(item.created_at)}
                  </p>
                </div>
              ))
            )}
          </div>
        ) : (
          <p className="muted">Choose an order to inspect its audit trail.</p>
        )}
      </section>
    </div>
  );
}

function formatTimestamp(raw: string): string {
  try {
    return new Date(raw).toLocaleString();
  } catch {
    return raw;
  }
}
