"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import {
  defaultOperatorPreferences,
  loadOperatorPreferences,
  saveOperatorPreferences,
  type OperatorPreferences,
  type VendorPreset,
} from "../shared/operator-preferences";
import type {
  AlpacaPaperReadiness,
  AnalysisRuntimeCatalog,
  AnalysisRuntimeHealth,
  AnalysisRuntimeProfile,
  AutomationState,
  PlatformPreflightSummary,
} from "../shared/contracts/analysis";

type SchedulerTargetMode = "paper_auto" | "paper_manual" | "analysis_only";

export function SettingsControlCenter() {
  const [readiness, setReadiness] = useState<AlpacaPaperReadiness | null>(null);
  const [automationState, setAutomationState] = useState<AutomationState | null>(null);
  const [runtimeProfile, setRuntimeProfile] = useState<AnalysisRuntimeProfile | null>(null);
  const [runtimeCatalog, setRuntimeCatalog] = useState<AnalysisRuntimeCatalog | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<AnalysisRuntimeHealth | null>(null);
  const [preflight, setPreflight] = useState<PlatformPreflightSummary | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [operator, setOperator] = useState("operator");
  const [liveReason, setLiveReason] = useState("Manual live readiness validation.");
  const [schedulerEnabled, setSchedulerEnabled] = useState(false);
  const [schedulerInterval, setSchedulerInterval] = useState("30");
  const [schedulerTargetMode, setSchedulerTargetMode] =
    useState<SchedulerTargetMode>("paper_auto");
  const [preferences, setPreferences] = useState<OperatorPreferences>(defaultOperatorPreferences);

  useEffect(() => {
    setPreferences(loadOperatorPreferences());
    void refresh();
  }, []);

  async function refresh() {
    setBusy("refresh");
    setError(null);

    try {
      const [
        readinessSnapshot,
        automationSnapshot,
        profileSnapshot,
        catalogSnapshot,
        healthSnapshot,
        preflightSnapshot,
      ] = await Promise.all([
        apiRequest<AlpacaPaperReadiness>("/brokers/alpaca/paper-readiness"),
        apiRequest<AutomationState>("/automation/state"),
        apiRequest<AnalysisRuntimeProfile>("/analysis/runtime-profile"),
        apiRequest<AnalysisRuntimeCatalog>("/analysis/runtime-catalog"),
        apiRequest<AnalysisRuntimeHealth>("/analysis/runtime-health"),
        apiRequest<PlatformPreflightSummary>("/diagnostics/preflight"),
      ]);

      setReadiness(readinessSnapshot);
      setAutomationState(automationSnapshot);
      setRuntimeProfile(profileSnapshot);
      setRuntimeCatalog(catalogSnapshot);
      setRuntimeHealth(healthSnapshot);
      setPreflight(preflightSnapshot);
      setSchedulerEnabled(automationSnapshot.scheduler.enabled);
      setSchedulerInterval(String(automationSnapshot.scheduler.interval_minutes));
      setSchedulerTargetMode(
        (automationSnapshot.scheduler.target_mode as SchedulerTargetMode) ?? "paper_auto",
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

  function savePreferences() {
    saveOperatorPreferences(preferences);
    setNotice("Operator defaults saved for analysis and paper workflows.");
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
          <span className="eyebrow">Preflight summary</span>
          <h2>Workflow gates</h2>
          <div className="stack">
            <StatusLine
              label="Analysis"
              value={preflight?.analysis.ready ? "Ready" : `Blocked (${preflight?.analysis.blocker_count ?? 0})`}
            />
            <StatusLine
              label="Paper manual"
              value={preflight?.paper_manual.ready ? "Ready" : `Blocked (${preflight?.paper_manual.blocker_count ?? 0})`}
            />
            <StatusLine
              label="Paper auto"
              value={preflight?.paper_auto.ready ? "Ready" : `Blocked (${preflight?.paper_auto.blocker_count ?? 0})`}
            />
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Analysis runtime</span>
          <h2>Provider and model profile</h2>
          <div className="stack">
            <StatusLine label="LLM provider" value={runtimeProfile?.llm_provider ?? "--"} />
            <StatusLine label="Deep model" value={runtimeProfile?.deep_think_llm ?? "--"} />
            <StatusLine label="Quick model" value={runtimeProfile?.quick_think_llm ?? "--"} />
            <StatusLine
              label="Core stock vendor"
              value={runtimeProfile?.data_vendors.core_stock_apis ?? "--"}
            />
            <StatusLine
              label="News vendor"
              value={runtimeProfile?.data_vendors.news_data ?? "--"}
            />
            <StatusLine
              label="Fallback policy"
              value={runtimeProfile?.vendor_fallback_policy ?? "--"}
            />
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Diagnostics</span>
          <h2>LLM and market data health</h2>
          <div className="stack">
            <div className="inline-panel">
              <strong>LLM • {runtimeHealth?.llm.state ?? "--"}</strong>
              <p>{runtimeHealth?.llm.message ?? "Waiting for runtime health."}</p>
              {runtimeHealth?.llm.recommended_action ? (
                <p>{runtimeHealth.llm.recommended_action}</p>
              ) : null}
            </div>
            <div className="inline-panel">
              <strong>Market data • {runtimeHealth?.market_data.state ?? "--"}</strong>
              <p>{runtimeHealth?.market_data.message ?? "Waiting for runtime health."}</p>
              {runtimeHealth?.market_data.recommended_action ? (
                <p>{runtimeHealth.market_data.recommended_action}</p>
              ) : null}
            </div>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Credential matrix</span>
          <h2>Provider readiness</h2>
          <div className="stack">
            {runtimeCatalog ? (
              Object.entries(runtimeCatalog.providers).map(([provider, config]) => (
                <div key={provider} className="inline-panel">
                  <strong>
                    {provider}
                    {runtimeProfile?.llm_provider === provider ? " • active" : ""}
                  </strong>
                  <p>
                    key env • {config.api_key_env ?? "--"} •{" "}
                    {runtimeProfile?.api_keys_present[provider] ? "present" : "missing"}
                  </p>
                  <p>{config.backend_url ?? "No backend URL registered."}</p>
                </div>
              ))
            ) : (
              <p className="muted">Runtime catalog is loading.</p>
            )}
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Strategy controls</span>
          <h2>Operator defaults and presets</h2>
          <div className="form-grid">
            <label className="field">
              <span>Default mode</span>
              <select
                value={preferences.defaultMode}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    defaultMode: event.target.value as OperatorPreferences["defaultMode"],
                  }))
                }
              >
                <option value="paper_manual">paper_manual</option>
                <option value="paper_auto">paper_auto</option>
                <option value="analysis_only">analysis_only</option>
              </select>
            </label>
            <label className="field">
              <span>Default symbol</span>
              <input
                value={preferences.defaultSymbol}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    defaultSymbol: event.target.value.toUpperCase(),
                  }))
                }
              />
            </label>
            <label className="field">
              <span>LLM provider preference</span>
              <input
                value={preferences.llmProviderPreference}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    llmProviderPreference: event.target.value,
                  }))
                }
                placeholder={runtimeProfile?.llm_provider ?? "leave empty for runtime default"}
              />
            </label>
            <label className="field">
              <span>Vendor preset</span>
              <select
                value={preferences.vendorPreset}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    vendorPreset: event.target.value as VendorPreset,
                  }))
                }
              >
                <option value="safe">safe</option>
                <option value="balanced">balanced</option>
                <option value="alpha_vantage_heavy">alpha_vantage_heavy</option>
              </select>
            </label>
            <label className="field">
              <span>Reference price default</span>
              <input
                value={preferences.defaultReferencePrice}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    defaultReferencePrice: event.target.value,
                  }))
                }
              />
            </label>
            <label className="field">
              <span>Limit price default</span>
              <input
                value={preferences.defaultLimitPrice}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    defaultLimitPrice: event.target.value,
                  }))
                }
              />
            </label>
          </div>
          <div className="inline-panel">
            <strong>Preset notes</strong>
            <p>
              safe keeps all data on yfinance, balanced uses Alpha Vantage for price and
              technical data, and alpha_vantage_heavy keeps fundamentals/news on yfinance
              while leaning harder on Alpha Vantage where your plan allows it.
            </p>
          </div>
          <div className="actions form-actions">
            <button className="button" type="button" onClick={savePreferences}>
              Save operator defaults
            </button>
            <Link href="/strategies" className="button-secondary">
              Open full strategy workspace
            </Link>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Data vendor profile</span>
          <h2>Category routing</h2>
          <div className="stack">
            {runtimeCatalog ? (
              runtimeCatalog.data_vendor_categories.map((category) => (
                <div key={category.category} className="inline-panel">
                  <strong>{category.label}</strong>
                  <p>
                    current •{" "}
                    {runtimeProfile?.data_vendors[category.category] ?? category.current_vendor}
                  </p>
                  <p>options • {category.options.join(", ")}</p>
                </div>
              ))
            ) : (
              <p className="muted">No data vendor catalog loaded yet.</p>
            )}
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Model shortlist</span>
          <h2>Active provider suggestions</h2>
          <div className="stack">
            {runtimeCatalog && runtimeProfile ? (
              <>
                <div className="inline-panel">
                  <strong>Quick models</strong>
                  <p>
                    {runtimeCatalog.providers[runtimeProfile.llm_provider]?.quick_models
                      .slice(0, 3)
                      .map((option) => option.value)
                      .join(", ") || "--"}
                  </p>
                </div>
                <div className="inline-panel">
                  <strong>Deep models</strong>
                  <p>
                    {runtimeCatalog.providers[runtimeProfile.llm_provider]?.deep_models
                      .slice(0, 3)
                      .map((option) => option.value)
                      .join(", ") || "--"}
                  </p>
                </div>
              </>
            ) : (
              <p className="muted">Runtime catalog is loading.</p>
            )}
          </div>
        </article>

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
