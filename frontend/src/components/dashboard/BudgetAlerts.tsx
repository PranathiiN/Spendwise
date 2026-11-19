import { Link } from "react-router";
import type { Budget } from "../../types";
import { STATUS_COLORS } from "../../utils/colors";
import { formatPercent } from "../../utils/currency";
import { ProgressBar } from "../common/ProgressBar";
import { StatusBadge } from "../common/StatusBadge";

interface BudgetAlertsProps {
  alerts: Budget[];
  budgetCount: number;
  format: (v: string) => string;
}

export function BudgetAlerts({ alerts, budgetCount, format }: BudgetAlertsProps) {
  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Budget alerts</h2>
        <Link to="/budgets" className="text-sm font-medium text-brand-700 hover:underline">Manage</Link>
      </div>
      {budgetCount === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">
          No budgets for this month.{" "}
          <Link to="/budgets" className="font-medium text-brand-700 hover:underline">Set one up</Link>
        </p>
      ) : alerts.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">All {budgetCount} budgets are on track.</p>
      ) : (
        <ul className="space-y-4">
          {alerts.map((b) => (
            <li key={b.id}>
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium text-slate-800">{b.category.name}</span>
                <StatusBadge status={b.status} />
              </div>
              <ProgressBar percent={b.percent_used} color={STATUS_COLORS[b.status]} marker={b.alert_threshold} label={`${b.category.name} budget used`} />
              <p className="mt-1 text-xs text-slate-500">
                {format(b.spent)} of {format(b.amount)} ({formatPercent(b.percent_used)})
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
