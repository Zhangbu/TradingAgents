"use client";

import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import type {
  AlpacaPaperReadiness,
  AutomationState,
} from "../shared/contracts/analysis";

type SchedulerTargetMode = "paper_auto" | "paper_manual" | "analysis_only";

export function SettingsControlCenter() {
  const [readiness, setReadiness] = useState<AlpacaPaperReadiness | null>(null);
  const [automationState, setAutomationState] = useState<AutomationState | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [operator, setOperator] = useState("operator");
  const [liveReason, setLiveReason] = useState("Manual live readiness validation.");
  const [schedulerEnabled, setSchedulerEnabled] = useState(false);
  const [schedulerInterval, setSchedulerInterval] = useState("30");
  const [schedulerTargetMode, setSchedulerTargetMode] =
    useState<SchedulerTargetMode>("paper_auto");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setBusy("refresh");
    setError(null);

    try {
      const [nextReadiness, nextAutomationState] = await Promise.all([
        apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
        apiRequest<AutomationState>("/automation/state"),
      ]);

      setReadiness(nextReadiness);
      setAutomationState(nextAutomationState);
      setSchedulerEnabled(nextAutomationState.scheduler.enabled);
      setSchedulerInterval(String(nextAutomationState.scheduler.interval_minutes));
      setSchedulerTargetMode(
        (nextAutomationState.scheduler.target_mode as SchedulerTargetMode) ?? "paper_auto",
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Settings load failed.");
    } finally {
      setBusy(null);
    }
  }

  async function testConnection() {
    setBusy("connection");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/brokers/alpaca/connect/test", { method: "POST" });
      await refresh();
      setNotice("Alpaca connection test succeeded.");
    } catch (connectionError) {
      setError(connectionError instanceof Error ? connectionError.message : "Connection test failed.");
      setBusy(null);
    }
  }

  async function toggleAutoTrading(enabled: boolean) {
    setBusy(enabled ? "auto-on" : "auto-off");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/auto-trading", {
        method: "POST",
        body: JSON.stringify({ enabled }),
      });
      await refresh();
      setNotice(enabled ? "Auto trading enabled." : "Auto trading disabled.");
    } catch (autoError) {
      setError(autoError instanceof Error ? autoError.message : "Auto trading update failed.");
      setBusy(null);
    }
  }

  async function toggleKillSwitch(active: boolean) {
    setBusy(active ? "kill-on" : "kill-off");
    setError(null);
    setNotice(null);

    try {
      await apiRequest(
        active ? "/automation/kill-switch/activate" : "/automation/kill-switch/release",
        active
          ? {
              method: "POST",
              body: JSON.stringify({ reason: "Manual operator stop from settings console." }),
            }
          : { method: "POST" },
      );
      await refresh();
      setNotice(active ? "Kill switch activated." : "Kill switch released.");
    } catch (killError) {
      setError(killError instanceof Error ? killError.message : "Kill switch update failed.");
      setBusy(null);
    }
  }

  async function recordBrokerSync() {
    setBusy("record-sync");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/broker-sync", {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refresh();
      setNotice("Broker sync timestamp refreshed.");
    } catch (syncError) {
      setError(syncError instanceof Error ? syncError.message : "Broker sync update failed.");
      setBusy(null);
    }
  }

  async function updateLiveTrading(enabled: boolean) {
    setBusy(enabled ? "live-on" : "live-off");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/live-trading", {
        method: "POST",
        body: JSON.stringify({
          enabled,
          actor: operator,
          reason: liveReason,
        }),
      });
      await refresh();
      setNotice(enabled ? "Live trading readiness enabled." : "Live trading readiness disabled.");
    } catch (liveError) {
      setError(liveError instanceof Error ? liveError.message : "Live trading update failed.");
      setBusy(null);
    }
  }

  async function confirmLiveTrading() {
    setBusy("live-confirm");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/live-trading/confirm", {
        method: "POST",
        body: JSON.stringify({ actor: operator }),
      });
      await refresh();
      setNotice("Live trading double confirmation recorded.");
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : "Live confirmation failed.");
      setBusy(null);
    }
  }

  async function updateScheduler() {
    setBusy("scheduler");
    setError(null);
    setNotice(null);

    try {
      await apiRequest("/automation/scheduler", {
        method: "POST",
        body: JSON.stringify({
          enabled: schedulerEnabled,
          interval_minutes: Number(schedulerInterval),
          target_mode: schedulerTargetMode,
        }),
      });
      await refresh();
      setNotice("Scheduler settings saved.");
    } catch (schedulerError) {
      setError(schedulerError instanceof Error ? schedulerError.message : "Scheduler update failed.");
      setBusy(null);
    }
  }

  return (
    <div className="stack">
      {(error || notice) && (
        <section className="section-tight">
          {error ? <div className="callout callout-error">{error}</div> : null}
          {notice ? <div className="callout callout-success">{notice}</div> : null}
        </section>
      )}

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Broker connection</span>
          <h2>Alpaca paper status</h2>
          <div className="stack">
            <StatusLine
              label="Connectivity"
              value={readiness?.broker_health.connectivity_ok ? "Connected" : "Check required"}
            />
            <StatusLine
              label="Integration mode"
              value={readiness?.broker_health.integration_mode ?? "--"}
            />
            <StatusLine
              label="Manual ready"
              value={readiness?.manual_ready ? "Yes" : "No"}
            />
            <StatusLine
              label="Auto ready"
              value={readiness?.auto_ready ? "Yes" : "No"}
            />
          </div>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void testConnection();
                });
              }}
              disabled={busy !== null}
            >
              Test connection
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void recordBrokerSync();
                });
              }}
              disabled={busy !== null}
            >
              Record broker sync
            </button>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">IB bridge</span>
          <h2>Interactive Brokers staging</h2>
          <div className="stack">
            <StatusLine label="Mode" value="Paper simulator" />
            <StatusLine label="Gateway state" value="Placeholder UI only" />
            <StatusLine label="Next step" value="Real TWS/Gateway connectivity" />
          </div>
          <div className="inline-panel">
            <strong>Why it is here already</strong>
            <p>
              The UI is reserving space for the second broker now so your terminal
              structure does not need to change again once IB live wiring begins.
            </p>
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Execution controls</span>
          <h2>Automation and kill switch</h2>
          <div className="stack">
            <StatusLine
              label="Auto trading"
              value={automationState?.auto_trading_enabled ? "Enabled" : "Disabled"}
            />
            <StatusLine
              label="Kill switch"
              value={automationState?.kill_switch_active ? "Active" : "Released"}
            />
            <StatusLine
              label="Broker sync healthy"
              value={automationState?.broker_sync_healthy ? "Healthy" : "Unhealthy"}
            />
            <StatusLine
              label="Consecutive failures"
              value={String(automationState?.consecutive_broker_failures ?? 0)}
            />
          </div>
          <div className="actions">
            <button className="button" type="button" onClick={() => startTransition(() => { void toggleAutoTrading(true); })} disabled={busy !== null}>
              Enable auto
            </button>
            <button className="button-secondary" type="button" onClick={() => startTransition(() => { void toggleAutoTrading(false); })} disabled={busy !== null}>
              Disable auto
            </button>
            <button className="button-secondary" type="button" onClick={() => startTransition(() => { void toggleKillSwitch(true); })} disabled={busy !== null}>
              Activate kill switch
            </button>
            <button className="button-secondary" type="button" onClick={() => startTransition(() => { void toggleKillSwitch(false); })} disabled={busy !== null}>
              Release kill switch
            </button>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Live manual readiness</span>
          <h2>Dual-control unlock path</h2>
          <div className="form-grid">
            <label className="field">
              <span>Actor</span>
              <input value={operator} onChange={(event) => setOperator(event.target.value)} />
            </label>
            <label className="field">
              <span>Reason</span>
              <input value={liveReason} onChange={(event) => setLiveReason(event.target.value)} />
            </label>
          </div>
          <div className="stack">
            <StatusLine
              label="Live enabled"
              value={automationState?.live_trading_enabled ? "Enabled" : "Disabled"}
            />
            <StatusLine
              label="Double confirmed"
              value={automationState?.live_trading_double_confirmed ? "Yes" : "No"}
            />
            <StatusLine
              label="Unlocked by"
              value={automationState?.live_trading_unlocked_by ?? "--"}
            />
          </div>
          <div className="actions">
            <button className="button" type="button" onClick={() => startTransition(() => { void updateLiveTrading(true); })} disabled={busy !== null}>
              Enable live readiness
            </button>
            <button className="button-secondary" type="button" onClick={() => startTransition(() => { void confirmLiveTrading(); })} disabled={busy !== null}>
              Confirm live readiness
            </button>
            <button className="button-secondary" type="button" onClick={() => startTransition(() => { void updateLiveTrading(false); })} disabled={busy !== null}>
              Disable live readiness
            </button>
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Scheduler</span>
          <h2>Automation cadence</h2>
          <div className="form-grid">
            <label className="field">
              <span>Enabled</span>
              <select
                value={schedulerEnabled ? "true" : "false"}
                onChange={(event) => setSchedulerEnabled(event.target.value === "true")}
              >
                <option value="true">enabled</option>
                <option value="false">disabled</option>
              </select>
            </label>
            <label className="field">
              <span>Interval minutes</span>
              <input
                value={schedulerInterval}
                onChange={(event) => setSchedulerInterval(event.target.value)}
              />
            </label>
            <label className="field field-span-2">
              <span>Target mode</span>
              <select
                value={schedulerTargetMode}
                onChange={(event) =>
                  setSchedulerTargetMode(event.target.value as SchedulerTargetMode)
                }
              >
                <option value="paper_auto">paper_auto</option>
                <option value="paper_manual">paper_manual</option>
                <option value="analysis_only">analysis_only</option>
              </select>
            </label>
          </div>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void updateScheduler();
                });
              }}
              disabled={busy !== null}
            >
              Save scheduler
            </button>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Risk policy snapshot</span>
          <h2>Current defaults</h2>
          <div className="stack">
            <StatusLine
              label="Sync stale threshold"
              value={`${automationState?.sync_stale_after_seconds ?? 0}s`}
            />
            <StatusLine
              label="Broker failure limit"
              value={String(automationState?.max_consecutive_broker_failures ?? 0)}
            />
            <StatusLine
              label="Scheduler target mode"
              value={automationState?.scheduler.target_mode ?? "--"}
            />
            <StatusLine
              label="Scheduler interval"
              value={`${automationState?.scheduler.interval_minutes ?? 0} min`}
            />
          </div>
          <div className="inline-panel">
            <strong>Readiness checklist</strong>
            <ul className="list">
              {(readiness?.checklist ?? ["Waiting for readiness data."]).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </article>
      </section>
    </div>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
