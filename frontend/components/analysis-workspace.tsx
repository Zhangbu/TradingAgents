"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import { getTodayDateInputValue } from "../lib/format";
import type {
  AnalysisRuntimeCatalog,
  AnalysisRuntimeHealth,
  AnalysisRuntimeProfile,
  AnalysisRunRecord,
  FailureDetails,
  RuntimeDataVendorCategory,
  RuntimeProviderCatalog,
  PlatformPreflightSummary,
  TradeIntentRecord,
} from "../shared/contracts/analysis";

type PlatformMode = "analysis_only" | "paper_manual" | "paper_auto";
type DataVendor = "yfinance" | "alpha_vantage";
type DataVendorMap = Record<string, DataVendor>;

export function AnalysisWorkspace() {
  const [symbol, setSymbol] = useState("AAPL");
  const [tradeDate, setTradeDate] = useState("");
  const [mode, setMode] = useState<PlatformMode>("paper_manual");
  const [llmProvider, setLlmProvider] = useState("");
  const [deepThinkModel, setDeepThinkModel] = useState("");
  const [quickThinkModel, setQuickThinkModel] = useState("");
  const [runtimeCatalog, setRuntimeCatalog] = useState<AnalysisRuntimeCatalog | null>(null);
  const [dataVendors, setDataVendors] = useState<DataVendorMap>({
    core_stock_apis: "alpha_vantage",
    technical_indicators: "alpha_vantage",
    fundamental_data: "alpha_vantage",
    news_data: "alpha_vantage",
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisRunRecord[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisRunRecord | null>(null);
  const [runtimeProfile, setRuntimeProfile] = useState<AnalysisRuntimeProfile | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<AnalysisRuntimeHealth | null>(null);
  const [preflight, setPreflight] = useState<PlatformPreflightSummary | null>(null);
  const [activeTradeIntent, setActiveTradeIntent] = useState<TradeIntentRecord | null>(
    null,
  );

  useEffect(() => {
    setTradeDate(getTodayDateInputValue());
    void Promise.all([refreshAnalysisHistory(), refreshRuntimeDiagnostics()]);
  }, []);

  useEffect(() => {
    if (!runtimeCatalog || !llmProvider) {
      return;
    }

    const provider = runtimeCatalog.providers[llmProvider];
    if (!provider) {
      return;
    }

    const knownDeepModels = new Set(provider.deep_models.map((option) => option.value));
    const knownQuickModels = new Set(provider.quick_models.map((option) => option.value));

    if (!deepThinkModel || (!knownDeepModels.has(deepThinkModel) && deepThinkModel !== "custom")) {
      const nextDeep = firstSuggestedModel(provider.deep_models);
      if (nextDeep) {
        setDeepThinkModel(nextDeep);
      }
    }

    if (!quickThinkModel || (!knownQuickModels.has(quickThinkModel) && quickThinkModel !== "custom")) {
      const nextQuick = firstSuggestedModel(provider.quick_models);
      if (nextQuick) {
        setQuickThinkModel(nextQuick);
      }
    }
  }, [runtimeCatalog, llmProvider, deepThinkModel, quickThinkModel]);

  async function refreshRuntimeDiagnostics() {
    try {
      const [profile, health, nextPreflight] = await Promise.all([
        apiRequest<AnalysisRuntimeProfile>("/analysis/runtime-profile"),
        apiRequest<AnalysisRuntimeHealth>("/analysis/runtime-health"),
        apiRequest<PlatformPreflightSummary>("/diagnostics/preflight"),
      ]);
      setRuntimeProfile(profile);
      setRuntimeHealth(health);
      setPreflight(nextPreflight);
      setLlmProvider(profile.llm_provider);
      setDeepThinkModel(profile.deep_think_llm);
      setQuickThinkModel(profile.quick_think_llm);
      setDataVendors({
        core_stock_apis: (profile.data_vendors.core_stock_apis as DataVendor) ?? "yfinance",
        technical_indicators:
          (profile.data_vendors.technical_indicators as DataVendor) ?? "yfinance",
        fundamental_data: (profile.data_vendors.fundamental_data as DataVendor) ?? "yfinance",
        news_data: (profile.data_vendors.news_data as DataVendor) ?? "yfinance",
      });
      const catalog = await apiRequest<AnalysisRuntimeCatalog>("/analysis/runtime-catalog");
      setRuntimeCatalog(catalog);
    } catch (runtimeError) {
      setError(
        runtimeError instanceof Error
          ? runtimeError.message
          : "Runtime diagnostics request failed.",
      );
    }
  }

  async function refreshAnalysisHistory() {
    setBusy("refresh");
    setError(null);

    try {
      const response = await apiRequest<{ items: AnalysisRunRecord[] }>(
        "/analysis/runs?limit=12",
      );
      setAnalyses(response.items);
      setActiveAnalysis((current) => current ?? response.items[0] ?? null);
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Analysis history request failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function launchAnalysis() {
    if (!runtimeProfile) {
      setError("Analysis runtime profile has not loaded yet. Refresh the page and try again.");
      return;
    }
    if (preflight && !preflight.analysis.ready) {
      const blocker =
        preflight.analysis.checks.find((check) => check.state === "blocked") ??
        preflight.analysis.checks[0];
      setError(blocker?.recommended_action ?? blocker?.message ?? "Analysis preflight is blocked.");
      return;
    }

    setBusy("analysis");
    setError(null);
    setNotice(null);
    setActiveTradeIntent(null);

    try {
      const run = await apiRequest<AnalysisRunRecord>("/analysis/runs", {
        method: "POST",
        body: JSON.stringify({
          symbol,
          trade_date: tradeDate,
          selected_analysts: ["market", "social", "news", "fundamentals"],
          llm_provider: llmProvider || runtimeProfile.llm_provider,
          deep_think_llm: deepThinkModel || runtimeProfile.deep_think_llm,
          quick_think_llm: quickThinkModel || runtimeProfile.quick_think_llm,
          data_vendors: dataVendors,
          mode,
        }),
      });
      setActiveAnalysis(run);
      await Promise.all([refreshAnalysisHistory(), refreshRuntimeDiagnostics()]);

      if (run.status === "failed") {
        setError(run.error_message ?? "Analysis execution failed.");
        return;
      }

      setNotice("Analysis run completed and saved.");
    } catch (analysisError) {
      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "Analysis execution failed.",
      );
      setBusy(null);
    }
  }

  async function createTradeIntent() {
    if (!activeAnalysis) {
      return;
    }

    setBusy("intent");
    setError(null);
    setNotice(null);

    try {
      const intent = await apiRequest<TradeIntentRecord>(
        `/trade-intents/from-analysis/${activeAnalysis.id}`,
        { method: "POST" },
      );
      setActiveTradeIntent(intent);
      setNotice("Trade intent generated from active analysis.");
    } catch (intentError) {
      setError(
        intentError instanceof Error
          ? intentError.message
          : "Trade intent generation failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function evaluateRisk() {
    if (!activeTradeIntent) {
      return;
    }

    setBusy("risk");
    setError(null);
    setNotice(null);

    try {
      const evaluated = await apiRequest<TradeIntentRecord>(
        `/trade-intents/${activeTradeIntent.id}/risk-evaluate`,
        { method: "POST" },
      );
      setActiveTradeIntent(evaluated);
      setNotice("Risk evaluation completed for the active trade intent.");
    } catch (riskError) {
      setError(
        riskError instanceof Error ? riskError.message : "Risk evaluation failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  const providerCatalog = runtimeCatalog?.providers[llmProvider] ?? null;
  const dominantFailure = activeAnalysis?.failure_details ?? null;

  return (
    <div className="stack">
      {(error || notice) && (
        <section className="section-tight">
          {error ? <div className="callout callout-error">{error}</div> : null}
          {notice ? <div className="callout callout-success">{notice}</div> : null}
        </section>
      )}

      <section className="grid columns-3">
        <article className="card">
          <span className="eyebrow">Launch</span>
          <h2>Run a fresh analysis</h2>
          <div className="form-grid">
            <label className="field">
              <span>Symbol</span>
              <input
                value={symbol}
                onChange={(event) => setSymbol(event.target.value.toUpperCase())}
              />
            </label>
            <label className="field">
              <span>Trade date</span>
              <input
                type="date"
                value={tradeDate}
                onChange={(event) => setTradeDate(event.target.value)}
              />
            </label>
            <label className="field field-span-2">
              <span>Mode</span>
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value as PlatformMode)}
              >
                <option value="analysis_only">analysis_only</option>
                <option value="paper_manual">paper_manual</option>
                <option value="paper_auto">paper_auto</option>
              </select>
            </label>
            <label className="field">
              <span>LLM provider</span>
              <select
                value={llmProvider}
                onChange={(event) => setLlmProvider(event.target.value)}
              >
                {runtimeCatalog
                  ? Object.keys(runtimeCatalog.providers).map((provider) => (
                      <option key={provider} value={provider}>
                        {provider}
                      </option>
                    ))
                  : null}
              </select>
            </label>
            <label className="field">
              <span>Deep think model</span>
              <select
                value={deepThinkModel}
                onChange={(event) => setDeepThinkModel(event.target.value)}
              >
                {renderModelOptions(providerCatalog, deepThinkModel)}
              </select>
            </label>
            <label className="field">
              <span>Quick think model</span>
              <select
                value={quickThinkModel}
                onChange={(event) => setQuickThinkModel(event.target.value)}
              >
                {renderQuickModelOptions(providerCatalog, quickThinkModel)}
              </select>
            </label>
            {providerCatalog && needsCustomModelInput(providerCatalog.deep_models, deepThinkModel) ? (
              <label className="field">
                <span>Custom deep model id</span>
                <input
                  value={deepThinkModel}
                  onChange={(event) => setDeepThinkModel(event.target.value)}
                />
              </label>
            ) : null}
            {providerCatalog && needsCustomModelInput(providerCatalog.quick_models, quickThinkModel) ? (
              <label className="field">
                <span>Custom quick model id</span>
                <input
                  value={quickThinkModel}
                  onChange={(event) => setQuickThinkModel(event.target.value)}
                />
              </label>
            ) : null}
          </div>
          <div className="stack section-tight">
            <span className="eyebrow">Data vendors by category</span>
            <div className="form-grid">
              {(runtimeCatalog?.data_vendor_categories ?? defaultVendorCategories()).map((category) => (
                <label key={category.category} className="field">
                  <span>{category.label}</span>
                  <select
                    value={dataVendors[category.category] ?? "yfinance"}
                    onChange={(event) =>
                      setDataVendors((current) => ({
                        ...current,
                        [category.category]: event.target.value as DataVendor,
                      }))
                    }
                  >
                    {category.options.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </div>
          <div className="actions form-actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void launchAnalysis();
                });
              }}
              disabled={busy !== null || runtimeProfile === null || preflight?.analysis.ready === false}
            >
              {busy === "analysis"
                ? "Running..."
                : runtimeProfile === null
                  ? "Loading runtime..."
                  : preflight?.analysis.ready === false
                    ? "Preflight blocked"
                  : "Run analysis"}
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void refreshAnalysisHistory();
                });
              }}
              disabled={busy !== null}
            >
              Refresh history
            </button>
          </div>
        </article>

        <article className="card span-2">
          <span className="eyebrow">Decision focus</span>
          <h2>Active analysis summary</h2>
          {runtimeHealth ? (
            <div className="grid columns-2 section-tight">
              <div className="inline-panel">
                <strong>
                  Runtime • {runtimeProfile?.llm_provider ?? llmProvider}
                </strong>
                <p>
                  {runtimeProfile?.deep_think_llm ?? deepThinkModel} /{" "}
                  {runtimeProfile?.quick_think_llm ?? quickThinkModel}
                </p>
                <p>
                  Core vendor •{" "}
                  {runtimeProfile?.data_vendors.core_stock_apis ?? dataVendors.core_stock_apis}
                </p>
                <p>
                  Fallback •{" "}
                  {runtimeProfile?.vendor_fallback_policy ??
                    "explicit_multi_vendor_only"}
                </p>
              </div>
              <div className="inline-panel">
                <strong>Health • {runtimeHealth.llm.state}</strong>
                <p>{runtimeHealth.llm.message}</p>
                {runtimeHealth.llm.recommended_action ? (
                  <p>{runtimeHealth.llm.recommended_action}</p>
                ) : null}
              </div>
              <div className="inline-panel">
                <strong>Market data • {runtimeHealth.market_data.state}</strong>
                <p>{runtimeHealth.market_data.message}</p>
                {runtimeHealth.market_data.recommended_action ? (
                  <p>{runtimeHealth.market_data.recommended_action}</p>
                ) : null}
                {renderVendorHealthHint(runtimeProfile?.data_vendors, dominantFailure)}
              </div>
              <div className="inline-panel">
                <strong>Preflight • {preflight?.analysis.state ?? "--"}</strong>
                <p>
                  {preflight?.analysis.ready
                    ? "Analysis can run with the current runtime profile."
                    : "Analysis is blocked until the failed preflight check is fixed."}
                </p>
                {preflight?.analysis.checks
                  .filter((check) => check.state !== "healthy")
                  .slice(0, 2)
                  .map((check) => (
                    <p key={check.component}>
                      {check.component}: {check.recommended_action ?? check.message}
                    </p>
                  ))}
              </div>
            </div>
          ) : null}
          {activeAnalysis ? (
            <div className="stack">
              <div className="inline-panel">
                <strong>
                  {activeAnalysis.symbol} • {activeAnalysis.mode}
                </strong>
                <p>
                  {activeAnalysis.status} • {activeAnalysis.id}
                </p>
                <p>
                  {activeAnalysis.llm_provider ?? llmProvider} •{" "}
                  {activeAnalysis.deep_think_llm ?? deepThinkModel} /{" "}
                  {activeAnalysis.quick_think_llm ?? quickThinkModel}
                </p>
                <p>
                  data •{" "}
                  {activeAnalysis.data_vendors?.core_stock_apis ??
                    runtimeProfile?.data_vendors.core_stock_apis ??
                    dataVendors.core_stock_apis}
                </p>
              </div>
              {activeAnalysis.error_message ? (
                <div className="callout callout-error">
                  {activeAnalysis.error_message}
                </div>
              ) : null}
              {dominantFailure ? <FailurePanel details={dominantFailure} /> : null}
              <div className="grid columns-2">
                <ArtifactBlock
                  title="Final decision"
                  body={
                    activeAnalysis.artifacts?.final_trade_decision ??
                    "No final trade decision text saved yet."
                  }
                />
                <ArtifactBlock
                  title="Processed signal"
                  body={
                    activeAnalysis.artifacts?.processed_signal ??
                    "No processed signal saved yet."
                  }
                />
                <ArtifactBlock
                  title="Investment plan"
                  body={
                    activeAnalysis.artifacts?.investment_plan ??
                    "No investment plan saved yet."
                  }
                />
                <ArtifactBlock
                  title="Fundamentals report"
                  body={
                    activeAnalysis.artifacts?.fundamentals_report ??
                    "No fundamentals report saved yet."
                  }
                />
              </div>
            </div>
          ) : (
            <p className="muted">No analysis run selected yet.</p>
          )}
        </article>
      </section>

      <section className="grid columns-3">
        <article className="card">
          <span className="eyebrow">History</span>
          <h2>Recent runs</h2>
          <div className="stack card-scroll">
            {analyses.length === 0 ? (
              <p className="muted">No saved runs yet.</p>
            ) : (
              analyses.map((analysis) => (
                <button
                  key={analysis.id}
                  className={`inline-panel text-left${
                    activeAnalysis?.id === analysis.id ? " panel-selected" : ""
                  }`}
                  type="button"
                  onClick={() => {
                    setActiveAnalysis(analysis);
                    setActiveTradeIntent(null);
                  }}
                >
                  <strong>{analysis.symbol}</strong>
                  <p>
                    {analysis.mode} • {analysis.status}
                  </p>
                </button>
              ))
            )}
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Structured signal</span>
          <h2>Trade intent</h2>
          <div className="actions form-actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void createTradeIntent();
                });
              }}
              disabled={busy !== null || !activeAnalysis}
            >
              {busy === "intent" ? "Generating..." : "Generate trade intent"}
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void evaluateRisk();
                });
              }}
              disabled={busy !== null || !activeTradeIntent}
            >
              {busy === "risk" ? "Evaluating..." : "Evaluate risk"}
            </button>
          </div>
          {activeTradeIntent ? (
            <div className="stack card-scroll">
              <div className="inline-panel">
                <strong>
                  {activeTradeIntent.side.toUpperCase()} • {activeTradeIntent.rating}
                </strong>
                <p>
                  {activeTradeIntent.status} • confidence{" "}
                  {Math.round(activeTradeIntent.confidence * 100)}%
                </p>
              </div>
              <div className="status-row">
                <span>Max position</span>
                <strong>{Math.round(activeTradeIntent.max_position_pct * 100)}%</strong>
              </div>
              <div className="status-row">
                <span>Loss cap</span>
                <strong>{Math.round(activeTradeIntent.max_loss_pct * 100)}%</strong>
              </div>
              <div className="status-row">
                <span>Take profit</span>
                <strong>{Math.round(activeTradeIntent.take_profit_pct * 100)}%</strong>
              </div>
              <div className="inline-panel">
                <strong>Thesis</strong>
                <p>{activeTradeIntent.thesis_summary}</p>
              </div>
            </div>
          ) : (
            <p className="muted">Generate a trade intent from the active analysis.</p>
          )}
        </article>

        <article className="card">
          <span className="eyebrow">Risk outcome</span>
          <h2>Execution gate</h2>
          {activeTradeIntent?.risk_summary ? (
            <div className="stack card-scroll">
              <div className="inline-panel">
                <strong>{activeTradeIntent.risk_summary.outcome}</strong>
                <p>
                  {activeTradeIntent.risk_flags.length > 0
                    ? activeTradeIntent.risk_flags.join(", ")
                    : "No elevated risk flags recorded."}
                </p>
              </div>
              {activeTradeIntent.risk_summary.checks.map((check) => (
                <div key={check.rule_code} className="inline-panel">
                  <strong>{check.rule_code}</strong>
                  <p>
                    {check.severity} • {check.outcome}
                  </p>
                  <p>{check.message}</p>
                </div>
              ))}
              <Link className="button" href="/paper">
                Continue to trading terminal
              </Link>
            </div>
          ) : (
            <p className="muted">
              Run a risk evaluation to see whether this analysis can move into the
              trading workflow.
            </p>
          )}
        </article>
      </section>
    </div>
  );
}

function renderModelOptions(
  providerCatalog: RuntimeProviderCatalog | null,
  currentValue: string,
) {
  const options = providerCatalog?.deep_models ?? [];
  return renderOptions(options, currentValue);
}

function renderQuickModelOptions(
  providerCatalog: RuntimeProviderCatalog | null,
  currentValue: string,
) {
  const options = providerCatalog?.quick_models ?? [];
  return renderOptions(options, currentValue);
}

function renderOptions(
  options: RuntimeProviderCatalog["deep_models"],
  currentValue: string,
) {
  const knownValues = new Set(options.map((option) => option.value));
  const rendered = options.map((option) => (
    <option key={option.value} value={option.value}>
      {option.label}
    </option>
  ));

  if (currentValue && !knownValues.has(currentValue)) {
    rendered.unshift(
      <option key={currentValue} value={currentValue}>
        {currentValue} (custom)
      </option>,
    );
  }

  return rendered;
}

function needsCustomModelInput(
  options: RuntimeProviderCatalog["deep_models"],
  currentValue: string,
) {
  return currentValue === "custom";
}

function firstSuggestedModel(options: RuntimeProviderCatalog["deep_models"]) {
  return options.find((option) => option.value !== "custom")?.value ?? options[0]?.value ?? "";
}

function defaultVendorCategories(): RuntimeDataVendorCategory[] {
  return [
    {
      category: "core_stock_apis",
      label: "Core stock prices",
      current_vendor: "yfinance",
      options: ["yfinance", "alpha_vantage"],
    },
    {
      category: "technical_indicators",
      label: "Technical indicators",
      current_vendor: "yfinance",
      options: ["yfinance", "alpha_vantage"],
    },
    {
      category: "fundamental_data",
      label: "Fundamentals",
      current_vendor: "yfinance",
      options: ["yfinance", "alpha_vantage"],
    },
    {
      category: "news_data",
      label: "News and sentiment",
      current_vendor: "yfinance",
      options: ["yfinance", "alpha_vantage"],
    },
  ];
}

function renderVendorHealthHint(
  dataVendors: Record<string, string> | undefined,
  failureDetails: FailureDetails | null,
) {
  if (!failureDetails) {
    return null;
  }

  if (failureDetails.code === "market_data_premium_endpoint") {
    return (
      <p>
        Current categories use alpha_vantage selectively. Premium endpoint failures
        usually mean at least one selected category is not available on the active plan.
      </p>
    );
  }

  if (failureDetails.code === "market_data_tls") {
    return (
      <p>
        yfinance is still active for at least one category:
        {" "}
        {Object.entries(dataVendors ?? {})
          .filter(([, vendor]) => vendor === "yfinance")
          .map(([category]) => category)
          .join(", ") || "unknown"}.
      </p>
    );
  }

  return null;
}

function FailurePanel({ details }: { details: FailureDetails }) {
  return (
    <div className="inline-panel">
      <strong>
        Failure • {details.code}
      </strong>
      <p>
        {details.component} • {details.category} •{" "}
        {details.retryable ? "retryable" : "operator action required"}
      </p>
      <p>{details.message}</p>
      {details.recommended_action ? <p>{details.recommended_action}</p> : null}
    </div>
  );
}

function ArtifactBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="inline-panel artifact-panel">
      <strong>{title}</strong>
      <div className="artifact-scroll">
        <p>{body}</p>
      </div>
    </div>
  );
}
