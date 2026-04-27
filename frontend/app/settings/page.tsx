import { SettingsControlCenter } from "../../components/settings-control-center";
import { TerminalShell } from "../../components/terminal-shell";

export default function SettingsPage() {
  return (
    <TerminalShell
      activeHref="/settings"
      title="System Configuration"
      subtitle="Manage Alpaca connectivity, execution controls, and the operational guardrails around your agent workflow."
    >
      <SettingsControlCenter />
    </TerminalShell>
  );
}
