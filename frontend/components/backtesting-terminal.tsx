export function BacktestingTerminal() {
  return (
    <div className="stack">
      <section className="grid columns-3">
        <article className="card span-2">
          <span className="eyebrow">Simulation pipeline</span>
          <h2>Backtesting terminal is staged next</h2>
          <div className="stack">
            <div className="inline-panel">
              <strong>Why it is not first</strong>
              <p>
                Alpaca paper and the live operator workflow are the current priority.
                Backtesting should plug into the same strategy, risk, and broker mental
                model once those production-facing paths are stable.
              </p>
            </div>
            <div className="inline-panel">
              <strong>Planned scope</strong>
              <p>
                Strategy parameter presets, historical run configuration, equity curve,
                drawdown analysis, and per-trade replay aligned with the TradingAgents
                signal contracts.
              </p>
            </div>
          </div>
        </article>

        <article className="card">
          <span className="eyebrow">Readiness</span>
          <h2>What we need first</h2>
          <ul className="list">
            <li>Stable signal contracts from the analysis workflow.</li>
            <li>Reusable risk policy settings shared with paper/live flows.</li>
            <li>Order and fill semantics that match execution mode.</li>
            <li>Historical market data and benchmark selection.</li>
          </ul>
        </article>
      </section>

      <section className="grid columns-4">
        <article className="card metric-card">
          <span className="eyebrow">Planned module</span>
          <p className="metric">Strategy Lab</p>
        </article>
        <article className="card metric-card">
          <span className="eyebrow">Target outputs</span>
          <p className="metric">PnL / DD</p>
        </article>
        <article className="card metric-card">
          <span className="eyebrow">Execution style</span>
          <p className="metric">Replay</p>
        </article>
        <article className="card metric-card">
          <span className="eyebrow">Status</span>
          <p className="metric">Queued</p>
        </article>
      </section>
    </div>
  );
}
