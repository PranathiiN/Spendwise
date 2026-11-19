import type { Budget } from "../../types";
import { STATUS_COLORS } from "../../utils/colors";
import { formatPercent, toNumber } from "../../utils/currency";
import { CategoryDot } from "../common/CategoryDot";
import { Icon } from "../common/Icon";
import { ProgressBar } from "../common/ProgressBar";
import { StatusBadge } from "../common/StatusBadge";

interface BudgetCardProps {
  budget: Budget;
  format: (v: string) => string;
  onEdit: () => void;
  onDelete: () => void;
}

export function BudgetCard({ budget, format, onEdit, onDelete }: BudgetCardProps) {
  const remaining = toNumber(budget.remaining);
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-3">
          <CategoryDot color={budget.category.color} name={budget.category.name} />
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{budget.category.name}</p>
            <StatusBadge status={budget.status} />
          </div>
        </div>
        <div className="flex shrink-0">
          <button type="button" className="btn-ghost" onClick={onEdit} aria-label={`Edit ${budget.category.name} budget`}>
            <Icon name="edit" className="h-4 w-4" />
          </button>
          <button type="button" className="btn-ghost hover:text-critical" onClick={onDelete} aria-label={`Delete ${budget.category.name} budget`}>
            <Icon name="trash" className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div>
        <div className="mb-1.5 flex items-baseline justify-between text-sm">
          <span className="font-semibold text-slate-900">{format(budget.spent)}</span>
          <span className="text-slate-500">of {format(budget.amount)}</span>
        </div>
        <ProgressBar percent={budget.percent_used} color={STATUS_COLORS[budget.status]} marker={budget.alert_threshold} label={`${budget.category.name} budget used`} />
        <div className="mt-1.5 flex justify-between text-xs text-slate-500">
          <span>{formatPercent(budget.percent_used)} used · alert at {budget.alert_threshold}%</span>
          <span className={remaining < 0 ? "font-medium text-[#a32727]" : ""}>
            {remaining < 0 ? `${format(String(Math.abs(remaining)))} over` : `${format(budget.remaining)} left`}
          </span>
        </div>
      </div>
    </div>
  );
}
