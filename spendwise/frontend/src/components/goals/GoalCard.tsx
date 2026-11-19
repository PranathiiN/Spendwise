import type { SavingsGoal } from "../../types";
import { formatPercent, toNumber } from "../../utils/currency";
import { formatDate } from "../../utils/dates";
import { Icon } from "../common/Icon";
import { ProgressBar } from "../common/ProgressBar";
import { StatusBadge } from "../common/StatusBadge";

interface GoalCardProps {
  goal: SavingsGoal;
  format: (v: string) => string;
  onDeposit: () => void;
  onWithdraw: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function timeLeft(goal: SavingsGoal): string | null {
  if (goal.days_remaining === null) return null;
  if (goal.is_completed) return null;
  if (goal.days_remaining < 0) return `${Math.abs(goal.days_remaining)} days past target`;
  if (goal.days_remaining === 0) return "Due today";
  return `${goal.days_remaining} days left`;
}

export function GoalCard({ goal, format, onDeposit, onWithdraw, onEdit, onDelete }: GoalCardProps) {
  const left = timeLeft(goal);
  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: goal.color }} aria-hidden="true" />
            <h3 className="truncate font-semibold text-slate-900">{goal.name}</h3>
          </div>
          <div className="mt-1"><StatusBadge status={goal.status} /></div>
        </div>
        <div className="flex shrink-0">
          <button type="button" className="btn-ghost" onClick={onEdit} aria-label={`Edit ${goal.name}`}>
            <Icon name="edit" className="h-4 w-4" />
          </button>
          <button type="button" className="btn-ghost hover:text-critical" onClick={onDelete} aria-label={`Delete ${goal.name}`}>
            <Icon name="trash" className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div>
        <div className="mb-1.5 flex items-baseline justify-between">
          <span className="text-xl font-bold text-slate-900">{format(goal.current_amount)}</span>
          <span className="text-sm text-slate-500">of {format(goal.target_amount)}</span>
        </div>
        <ProgressBar percent={goal.progress_percent} color={goal.color} label={`${goal.name} progress`} />
        <p className="mt-1.5 text-xs text-slate-500">{formatPercent(goal.progress_percent)} complete</p>
      </div>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <dt className="text-xs text-slate-500">Remaining</dt>
          <dd className="font-medium text-slate-800">{format(goal.remaining_amount)}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Target date</dt>
          <dd className="font-medium text-slate-800">{formatDate(goal.target_date)}</dd>
        </div>
        {goal.monthly_required && toNumber(goal.monthly_required) > 0 && (
          <div className="col-span-2">
            <dt className="text-xs text-slate-500">Save per month to stay on track</dt>
            <dd className="font-medium text-slate-800">{format(goal.monthly_required)}</dd>
          </div>
        )}
      </dl>
      {left && <p className="text-xs text-slate-500">{left}</p>}
      {goal.notes && <p className="text-xs text-slate-500 italic">{goal.notes}</p>}

      <div className="mt-auto flex gap-2">
        <button type="button" className="btn-primary flex-1" onClick={onDeposit}>
          <Icon name="plus" className="h-4 w-4" /> Add money
        </button>
        <button type="button" className="btn-secondary flex-1" onClick={onWithdraw} disabled={toNumber(goal.current_amount) <= 0}>
          Withdraw
        </button>
      </div>
    </div>
  );
}
