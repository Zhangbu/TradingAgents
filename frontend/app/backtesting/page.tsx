import { BacktestingTerminal } from "../../components/backtesting-terminal";
import { TerminalShell } from "../../components/terminal-shell";

export default function BacktestingPage() {
  return (
    <TerminalShell
      activeHref="/backtesting"
      title={{ en: "Backtesting", zh: "回测" }}
      subtitle={{
        en: "Keep the simulation workspace nearby while the paper workflow continues to mature.",
        zh: "在模拟盘工作流逐步稳定的同时，保留回测工作区入口。",
      }}
    >
      <BacktestingTerminal />
    </TerminalShell>
  );
}
