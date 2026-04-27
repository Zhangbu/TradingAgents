import Link from "next/link";
import { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/analysis", label: "Market Analysis" },
  { href: "/paper", label: "Trading" },
  { href: "/orders-audit", label: "Orders & Audit" },
  { href: "/settings", label: "Settings" },
  { href: "/backtesting", label: "Backtesting" },
];

export function TerminalShell({
  activeHref,
  title,
  subtitle,
  children,
}: {
  activeHref: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <main className="terminal-shell">
      <aside className="terminal-sidebar">
        <div className="brand-block">
          <span className="brand-mark">QuantTerminal</span>
          <span className="brand-version">v1.0.4-pro</span>
        </div>

        <nav className="terminal-nav">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`terminal-nav-item${item.href === activeHref ? " is-active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="sidebar-card">
          <p className="sidebar-label">Operator</p>
          <strong>Trader #042</strong>
          <p className="muted">Paper mode operator console</p>
        </div>
      </aside>

      <section className="terminal-main">
        <header className="terminal-topbar">
          <label className="terminal-search">
            <span>Search symbols, agents, or reports...</span>
          </label>
          <div className="terminal-meta">
            <span className="broker-dot" />
            <span>Broker: Alpaca</span>
            <span className="meta-separator" />
            <span>Paper workflow</span>
          </div>
        </header>

        <section className="terminal-content">
          <div className="page-heading">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          {children}
        </section>
      </section>
    </main>
  );
}
