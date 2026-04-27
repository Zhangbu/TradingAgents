import { AlpacaPaperConsole } from "../../components/alpaca-paper-console";
import { TerminalShell } from "../../components/terminal-shell";

export default function PaperPage() {
  return (
    <TerminalShell
      activeHref="/paper"
      title="Trading Terminal"
      subtitle="Operate the Alpaca paper workflow with readiness checks, order supervision, and account-state visibility."
    >
      <AlpacaPaperConsole />
    </TerminalShell>
  );
}
