"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { apiRequest, authEnabled } from "../lib/api";
import {
  LocalizedText,
  resolveLocalizedText,
  UiLanguageProvider,
  useUiLanguage,
} from "../shared/ui-language";

const navItems = [
  { id: "dashboard", href: "/", label: { en: "Dashboard", zh: "总览" } },
  { id: "analysis", href: "/analysis", label: { en: "Analysis", zh: "分析" } },
  { id: "paper", href: "/paper", label: { en: "Paper", zh: "模拟盘" } },
  { id: "settings", href: "/settings", label: { en: "Settings", zh: "设置" } },
  { id: "backtesting", href: "/backtesting", label: { en: "Backtesting", zh: "回测" } },
] as const;

type SessionResponse = {
  auth_enabled: boolean;
  authenticated: boolean;
  username?: string | null;
};

function ShellContent({
  activeTab,
  activeHref,
  onTabChange,
  title,
  subtitle,
  children,
}: {
  activeTab?: string;
  activeHref?: string;
  onTabChange?: (tab: string) => void;
  title: LocalizedText;
  subtitle: LocalizedText;
  children: ReactNode;
}) {
  const router = useRouter();
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const { locale, setLocale, text } = useUiLanguage();

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
          <span className="eyebrow">{text({ en: "Session check", zh: "会话检查" })}</span>
          <h1>{text({ en: "Validating operator access…", zh: "正在验证操作员访问权限…" })}</h1>
          <p>
            {text({
              en: "Hold on while the terminal confirms your authenticated session.",
              zh: "正在确认你的登录会话，请稍候。",
            })}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="terminal-shell">
      <aside className="terminal-sidebar">
        <div className="brand-block">
          <span className="brand-mark">QuantTerminal</span>
          <span className="brand-version">
            {text({ en: "self-use workspace", zh: "自用工作台" })}
          </span>
        </div>

        <nav className="terminal-nav">
          {navItems.map((item) => {
            const active = item.id === activeTab || item.href === activeHref;
            if (onTabChange) {
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`terminal-nav-item${active ? " is-active" : ""}`}
                  onClick={() => {
                    onTabChange(item.id);
                  }}
                >
                  {text(item.label)}
                </button>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`terminal-nav-item${active ? " is-active" : ""}`}
              >
                {text(item.label)}
              </Link>
            );
          })}
        </nav>
      </aside>

      <section className="terminal-main">
        <header className="terminal-topbar">
          <div className="terminal-topbar-copy">
            <strong>{text({ en: "Operator terminal", zh: "交易工作台" })}</strong>
            <span>
              {text({
                en: "Keep the workflow short: analyze, review, execute.",
                zh: "保持链路简洁：分析、复核、执行。",
              })}
            </span>
          </div>
          <div className="terminal-meta">
            <span className="broker-dot" />
            <span>{text({ en: "Broker: Alpaca", zh: "券商：Alpaca" })}</span>
            <span className="meta-separator" />
            <span>{text({ en: "Paper workflow", zh: "模拟盘流程" })}</span>
            {session?.username ? (
              <>
                <span className="meta-separator" />
                <span>
                  {text({ en: "Operator", zh: "操作员" })}: {session.username}
                </span>
              </>
            ) : null}
            <div className="locale-toggle" aria-label="UI locale switch">
              <button
                type="button"
                className={`locale-toggle-button${locale === "en" ? " is-active" : ""}`}
                onClick={() => {
                  setLocale("en");
                }}
              >
                EN
              </button>
              <button
                type="button"
                className={`locale-toggle-button${locale === "zh" ? " is-active" : ""}`}
                onClick={() => {
                  setLocale("zh");
                }}
              >
                中文
              </button>
            </div>
            {authEnabled ? (
              <button
                type="button"
                className="topbar-logout"
                onClick={() => {
                  void logout();
                }}
                disabled={loggingOut}
              >
                {loggingOut
                  ? text({ en: "Signing out…", zh: "正在退出…" })
                  : text({ en: "Sign out", zh: "退出登录" })}
              </button>
            ) : null}
          </div>
        </header>

        <section className="terminal-content">
          <div className="page-heading">
            <h1>{resolveLocalizedText(locale, title)}</h1>
            <p>{resolveLocalizedText(locale, subtitle)}</p>
          </div>
          {children}
        </section>
      </section>
    </main>
  );
}

export function TerminalShell({
  activeTab,
  activeHref,
  onTabChange,
  title,
  subtitle,
  children,
}: {
  activeTab?: string;
  activeHref?: string;
  onTabChange?: (tab: string) => void;
  title: LocalizedText;
  subtitle: LocalizedText;
  children: ReactNode;
}) {
  return (
    <UiLanguageProvider>
      <ShellContent
        activeTab={activeTab}
        activeHref={activeHref}
        onTabChange={onTabChange}
        title={title}
        subtitle={subtitle}
      >
        {children}
      </ShellContent>
    </UiLanguageProvider>
  );
}
