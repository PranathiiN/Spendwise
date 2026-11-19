import type { BudgetStatus, GoalStatus } from "../../types";
import { Icon, type IconName } from "./Icon";

type AnyStatus = BudgetStatus | GoalStatus;

const CONFIG: Record<AnyStatus, { label: string; icon: IconName; className: string }> = {
  ok: { label: "On track", icon: "check", className: "bg-good/10 text-[#086b08]" },
  warning: { label: "Near limit", icon: "alert", className: "bg-warning/20 text-[#8a5a00]" },
  exceeded: { label: "Over budget", icon: "alert", className: "bg-critical/10 text-[#a32727]" },
  active: { label: "In progress", icon: "target", className: "bg-income/10 text-[#1d5aa3]" },
  completed: { label: "Completed", icon: "check", className: "bg-good/10 text-[#086b08]" },
  overdue: { label: "Overdue", icon: "alert", className: "bg-critical/10 text-[#a32727]" },
};

/** Status is never shown by color alone: every badge has an icon and a text label. */
export function StatusBadge({ status }: { status: AnyStatus }) {
  const cfg = CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.className}`}>
      <Icon name={cfg.icon} className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  );
}
