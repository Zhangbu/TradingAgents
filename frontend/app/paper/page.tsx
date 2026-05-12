import { AlpacaPaperConsole } from "../../components/alpaca-paper-console";
import { TerminalShell } from "../../components/terminal-shell";

export default function PaperPage() {
  return (
    <TerminalShell
      activeHref="/paper"
      title={{ en: "Paper Trading", zh: "模拟盘" }}
      subtitle={{
        en: "Run manual or auto paper workflows, supervise orders, and keep broker sync in view.",
        zh: "运行手动或自动模拟盘流程、监督订单，并持续关注券商同步状态。",
      }}
    >
      <AlpacaPaperConsole />
    </TerminalShell>
  );
}
