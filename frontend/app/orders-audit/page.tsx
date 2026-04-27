import { OrdersAuditWorkbench } from "../../components/orders-audit-workbench";
import { TerminalShell } from "../../components/terminal-shell";

export default function OrdersAuditPage() {
  return (
    <TerminalShell
      activeHref="/orders-audit"
      title="Orders & Audit"
      subtitle="Review order lifecycle changes, broker sync outcomes, and the operator trail behind every execution decision."
    >
      <OrdersAuditWorkbench />
    </TerminalShell>
  );
}
