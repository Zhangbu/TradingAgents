import { StrategyWorkbench } from "../../components/strategy-workbench";
import { TerminalShell } from "../../components/terminal-shell";

export default function StrategiesPage() {
  return (
    <TerminalShell
      activeHref="/strategies"
      title="Strategy Controls"
      subtitle="Set the defaults, presets, and execution posture that shape your daily paper workflow."
    >
      <StrategyWorkbench />
    </TerminalShell>
  );
}
