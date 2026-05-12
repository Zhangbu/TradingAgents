import { SettingsControlCenter } from "../../components/settings-control-center";
import { TerminalShell } from "../../components/terminal-shell";

export default function SettingsPage() {
  return (
    <TerminalShell
      activeHref="/settings"
      title={{ en: "Settings", zh: "设置" }}
      subtitle={{
        en: "Keep runtime controls, broker connectivity, defaults, and guardrails in one place.",
        zh: "把运行控制、券商连接、默认参数和安全边界集中到一个地方。",
      }}
    >
      <SettingsControlCenter />
    </TerminalShell>
  );
}
