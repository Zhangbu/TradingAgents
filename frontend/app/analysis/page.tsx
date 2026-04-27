import { AnalysisWorkspace } from "../../components/analysis-workspace";
import { TerminalShell } from "../../components/terminal-shell";

export default function AnalysisPage() {
  return (
    <TerminalShell
      activeHref="/analysis"
      title="Market Analysis Terminal"
      subtitle="Run TradingAgents analysis, generate structured trade intents, and decide whether an opportunity is ready to move into the trading workflow."
    >
      <AnalysisWorkspace />
    </TerminalShell>
  );
}
