"use client";

import Link from "next/link";

import { useUiLanguage } from "../shared/ui-language";

export function HomeHero() {
  const { text } = useUiLanguage();

  return (
    <section className="hero">
      <span className="eyebrow">TradingAgents</span>
      <h1 className="hero-title-tight">
        {text({
          en: "Keep the daily workflow short and readable.",
          zh: "把每日工作流保持得简洁、清晰。",
        })}
      </h1>
      <p>
        {text({
          en: "Start from the account state, move into analysis only when needed, and use the paper workflow when a setup is ready.",
          zh: "先从账户状态开始，只在需要时进入分析，在机会成熟后再进入模拟盘流程。",
        })}
      </p>
      <div className="actions">
        <Link href="/analysis" className="button">
          {text({ en: "Open analysis", zh: "进入分析" })}
        </Link>
        <Link href="/paper" className="button-secondary">
          {text({ en: "Open paper workflow", zh: "进入模拟盘" })}
        </Link>
      </div>
    </section>
  );
}
