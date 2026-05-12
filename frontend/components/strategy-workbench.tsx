"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import type { AnalysisRuntimeCatalog, AnalysisRuntimeProfile } from "../shared/contracts/analysis";
import {
  defaultOperatorPreferences,
  loadOperatorPreferences,
  saveOperatorPreferences,
  type OperatorPreferences,
  type VendorPreset,
} from "../shared/operator-preferences";

const presetNotes: Record<VendorPreset, string> = {
  safe: "Use yfinance across all categories when you want the lowest setup friction and are mainly testing workflow behavior.",
  balanced:
    "Use Alpha Vantage for core prices and technicals, while keeping fundamentals and news on yfinance to avoid premium endpoint surprises.",
  alpha_vantage_heavy:
    "Lean harder on Alpha Vantage for market structure while leaving fundamentals and news on yfinance for better free-tier compatibility.",
};

export function StrategyWorkbench() {
  const [preferences, setPreferences] = useState<OperatorPreferences>(defaultOperatorPreferences);
  const [runtimeProfile, setRuntimeProfile] = useState<AnalysisRuntimeProfile | null>(null);
  const [runtimeCatalog, setRuntimeCatalog] = useState<AnalysisRuntimeCatalog | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPreferences(loadOperatorPreferences());
    void loadRuntime();
  }, []);

  async function loadRuntime() {
    try {
      const [profile, catalog] = await Promise.all([
        apiRequest<AnalysisRuntimeProfile>("/analysis/runtime-profile"),
        apiRequest<AnalysisRuntimeCatalog>("/analysis/runtime-catalog"),
      ]);
      setRuntimeProfile(profile);
      setRuntimeCatalog(catalog);
    } catch (runtimeError) {
      setError(
        runtimeError instanceof Error
          ? runtimeError.message
          : "Failed to load runtime context.",
      );
    }
  }

  function persist(next: OperatorPreferences) {
    setPreferences(next);
    saveOperatorPreferences(next);
    setNotice("Strategy defaults saved for analysis and paper workflows.");
    setError(null);
  }

  const activeProviderCatalog =
    runtimeCatalog?.providers[preferences.llmProviderPreference || runtimeProfile?.llm_provider || ""] ?? null;

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
          <span className="eyebrow">Workflow defaults</span>
          <h2>Operator strategy profile</h2>
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
              <span>Default broker</span>
              <select
                value={preferences.defaultBroker}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    defaultBroker: event.target.value as OperatorPreferences["defaultBroker"],
                  }))
                }
              >
                <option value="alpaca">alpaca</option>
                <option value="interactive_brokers">interactive_brokers</option>
              </select>
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
              <span>Reference price</span>
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
              <span>Limit price</span>
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
          <div className="actions form-actions">
            <button className="button" type="button" onClick={() => persist(preferences)}>
              Save strategy defaults
            </button>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Preset guidance</span>
          <h2>Data vendor operating modes</h2>
          <div className="stack">
            {(["safe", "balanced", "alpha_vantage_heavy"] as VendorPreset[]).map((preset) => (
              <div key={preset} className="inline-panel">
                <strong>
                  {preset}
                  {preferences.vendorPreset === preset ? " • active" : ""}
                </strong>
                <p>{presetNotes[preset]}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid columns-2">
        <article className="card">
          <span className="eyebrow">Provider profile</span>
          <h2>Default model posture</h2>
          <div className="form-grid">
            <label className="field">
              <span>Provider preference</span>
              <input
                value={preferences.llmProviderPreference}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    llmProviderPreference: event.target.value,
                  }))
                }
                placeholder={runtimeProfile?.llm_provider ?? "runtime default"}
              />
            </label>
            <label className="field">
              <span>Operator notes</span>
              <input
                value={preferences.notes}
                onChange={(event) =>
                  setPreferences((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                placeholder="Optional runbook or preference note"
              />
            </label>
          </div>
          <div className="actions form-actions">
            <button className="button" type="button" onClick={() => persist(preferences)}>
              Save provider preferences
            </button>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Model shortlist</span>
          <h2>Suggested models for the active profile</h2>
          {activeProviderCatalog ? (
            <div className="stack">
              <div className="inline-panel">
                <strong>Quick models</strong>
                <p>
                  {activeProviderCatalog.quick_models
                    .slice(0, 4)
                    .map((option) => option.value)
                    .join(", ")}
                </p>
              </div>
              <div className="inline-panel">
                <strong>Deep models</strong>
                <p>
                  {activeProviderCatalog.deep_models
                    .slice(0, 4)
                    .map((option) => option.value)
                    .join(", ")}
                </p>
              </div>
            </div>
          ) : (
            <p className="muted">Provider catalog is loading or the provider preference is custom.</p>
          )}
        </article>
      </section>
    </div>
  );
}
