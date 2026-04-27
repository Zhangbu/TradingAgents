import { BacktestingTerminal } from "../../components/backtesting-terminal";
import { TerminalShell } from "../../components/terminal-shell";

export default function BacktestingPage() {
  return (
    <TerminalShell
      activeHref="/backtesting"
      title="Backtesting Terminal"
      subtitle="A planned simulation workspace that will reuse the same strategy, signal, and risk semantics as the live operator workflow."
    >
      <BacktestingTerminal />
    </TerminalShell>
  );
}
