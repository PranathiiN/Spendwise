import { Link } from "react-router";
import type { DashboardData } from "../../types";
import { formatPercent } from "../../utils/currency";
import { formatDate } from "../../utils/dates";
import { ProgressBar } from "../common/ProgressBar";

interface GoalsOverviewProps {
  goals: DashboardData["goals"];
  summary: DashboardData["goals_summary"];
  format: (v: string) => string;
}

export function GoalsOverview({ goals, summary, format }: GoalsOverviewProps) {
  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Savings goals</h2>
        <Link to="/goals" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>
      </div>
      <p className="mb-4 text-sm text-slate-500">
        {format(summary.total_saved)} saved of {format(summary.total_target)} ·{" "}
        {summary.active_count} active, {summary.completed_count} completed
      </p>
      {goals.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-500">
          No active goals.{" "}
          <Link to="/goals" className="font-medium text-brand-700 hover:underline">Create one</Link>
        </p>
      ) : (
        <ul className="space-y-4">
          {goals.map((g) => (
            <li key={g.id}>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{g.name}</span>
                <span className="text-slate-500">{formatPercent(g.progress_percent)}</span>
              </div>
              <ProgressBar percent={g.progress_percent} color={g.color} label={`${g.name} progress`} />
              <p className="mt-1 text-xs text-slate-500">
                {format(g.current_amount)} of {format(g.target_amount)}
                {g.target_date && ` · by ${formatDate(g.target_date)}`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
