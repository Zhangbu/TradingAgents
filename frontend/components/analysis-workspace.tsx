"use client";

import Link from "next/link";
import { startTransition, useEffect, useState } from "react";

import { apiRequest } from "../lib/api";
import type {
  AnalysisRunRecord,
  TradeIntentRecord,
} from "../shared/contracts/analysis";

type PlatformMode = "analysis_only" | "paper_manual" | "paper_auto";

export function AnalysisWorkspace() {
  const [symbol, setSymbol] = useState("AAPL");
  const [tradeDate, setTradeDate] = useState("2026-04-26");
  const [mode, setMode] = useState<PlatformMode>("paper_manual");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisRunRecord[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<AnalysisRunRecord | null>(null);
  const [activeTradeIntent, setActiveTradeIntent] = useState<TradeIntentRecord | null>(
    null,
  );

  useEffect(() => {
    void refreshAnalysisHistory();
  }, []);

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
          mode,
        }),
      });
      setActiveAnalysis(run);
      await refreshAnalysisHistory();

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
          </div>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => {
                startTransition(() => {
                  void launchAnalysis();
                });
              }}
              disabled={busy !== null}
            >
              {busy === "analysis" ? "Running..." : "Run analysis"}
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
          {activeAnalysis ? (
            <div className="stack">
              <div className="inline-panel">
                <strong>
                  {activeAnalysis.symbol} • {activeAnalysis.mode}
                </strong>
                <p>
                  {activeAnalysis.status} • {activeAnalysis.id}
                </p>
              </div>
              {activeAnalysis.error_message ? (
                <div className="callout callout-error">
                  {activeAnalysis.error_message}
                </div>
              ) : null}
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
          <div className="stack">
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
          <div className="actions">
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
            <div className="stack">
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
            <div className="stack">
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

function ArtifactBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="inline-panel">
      <strong>{title}</strong>
      <p>{body}</p>
    </div>
  );
}
