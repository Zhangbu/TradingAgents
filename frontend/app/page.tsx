import Link from "next/link";
import { DashboardOverview } from "../components/dashboard-overview";
import { TerminalShell } from "../components/terminal-shell";

const features = [
  {
    title: "Research Core",
    body: "The existing TradingAgents graph becomes a web-triggered analysis engine with persistent run history.",
  },
  {
    title: "Hard Risk Gates",
    body: "Every intent is routed through deterministic checks before it can become an order.",
  },
  {
    title: "Broker Execution",
    body: "Alpaca and Interactive Brokers will sit behind a single adapter contract for paper and live modes.",
  },
];

export default function HomePage() {
  return (
    <TerminalShell
      activeHref="/"
      title="Portfolio Command Center"
      subtitle="A single operator surface for research, Alpaca paper execution, and the guardrails that sit between them."
    >
      <section className="hero">
        <span className="eyebrow">TradingAgents Platform</span>
        <h1>Research, paper execution, and operator controls in one cockpit.</h1>
        <p>
          The platform has moved past scaffolding. Alpaca paper is now wired end to
          end, and the frontend is evolving into an operator console that can launch,
          approve, sync, and supervise paper flows from one desk.
        </p>
        <div className="actions">
          <Link href="/analysis" className="button">
            Open analysis workspace
          </Link>
          <Link href="/paper" className="button-secondary">
            Open Alpaca paper console
          </Link>
          <a href="http://localhost:8000/api/health" className="button-secondary">
            API health endpoint
          </a>
        </div>
      </section>

      <section className="section">
        <div className="grid columns-3">
          {features.map((feature) => (
            <article key={feature.title} className="card">
              <h2>{feature.title}</h2>
              <p>{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <DashboardOverview />
      </section>
    </TerminalShell>
  );
}
