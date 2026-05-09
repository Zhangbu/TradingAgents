"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { apiRequest, authEnabled } from "../lib/api";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/analysis", label: "Market Analysis" },
  { href: "/paper", label: "Trading" },
  { href: "/orders-audit", label: "Orders & Audit" },
  { href: "/settings", label: "Settings" },
  { href: "/backtesting", label: "Backtesting" },
];

type SessionResponse = {
  auth_enabled: boolean;
  authenticated: boolean;
  username?: string | null;
};

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
  const router = useRouter();
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      if (!authEnabled) {
        setSession({ auth_enabled: false, authenticated: true, username: "operator" });
        return;
      }

      try {
        const nextSession = await apiRequest<SessionResponse>("/auth/session");
        if (cancelled) {
          return;
        }
        setSession(nextSession);
        if (!nextSession.authenticated) {
          router.replace("/login");
        }
      } catch {
        if (!cancelled) {
          router.replace("/login");
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function logout() {
    setLoggingOut(true);
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
    }
  }

  if (authEnabled && session === null) {
    return (
      <main className="auth-shell">
        <div className="auth-card">
          <span className="eyebrow">Session check</span>
          <h1>Validating operator access…</h1>
          <p>Hold on while the terminal confirms your authenticated session.</p>
        </div>
      </main>
    );
  }

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
            {session?.username ? (
              <>
                <span className="meta-separator" />
                <span>Operator: {session.username}</span>
              </>
            ) : null}
            {authEnabled ? (
              <button
                type="button"
                className="topbar-logout"
                onClick={() => {
                  void logout();
                }}
                disabled={loggingOut}
              >
                {loggingOut ? "Signing out..." : "Sign out"}
              </button>
            ) : null}
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
