import { DashboardOverview } from "../components/dashboard-overview";
import { HomeHero } from "../components/home-hero";
import { TerminalShell } from "../components/terminal-shell";

export default function HomePage() {
  return (
    <TerminalShell
      activeHref="/"
      title={{ en: "Command Center", zh: "交易总控台" }}
      subtitle={{
        en: "Check broker balances, workflow readiness, and today's attention items before going deeper.",
        zh: "先看券商账户、流程状态和今天需要处理的事项，再决定是否深入操作。",
      }}
    >
      <HomeHero />

      <section className="section">
        <DashboardOverview />
      </section>
    </TerminalShell>
  );
}
