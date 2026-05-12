import { AnalysisWorkspace } from "../../components/analysis-workspace";
import { TerminalShell } from "../../components/terminal-shell";

export default function AnalysisPage() {
  return (
    <TerminalShell
      activeHref="/analysis"
      title={{ en: "Analysis", zh: "分析" }}
      subtitle={{
        en: "Run research, inspect the signal, and decide whether an opportunity is ready for paper execution.",
        zh: "运行研究、查看信号，并判断一个机会是否适合进入模拟盘执行。",
      }}
    >
      <AnalysisWorkspace />
    </TerminalShell>
  );
}
