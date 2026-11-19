import type { Forecast } from "../../types";
import { formatDate } from "../../utils/dates";
import { Icon } from "../common/Icon";
import { StatusBadge } from "../common/StatusBadge";

interface ForecastCardProps {
  forecast: Forecast;
  format: (value: string | number | null | undefined, compact?: boolean) => string;
}

/** SW-15: end-of-month estimates for spending, budgets and savings goals. */
export function ForecastCard({ forecast, format }: ForecastCardProps) {
  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <Icon name="trendUp" className="h-5 w-5 text-brand-700" /> Month-end forecast
        </h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">Estimate</span>
      </div>

      {!forecast.available ? (
        <p className="text-sm text-slate-500">{forecast.reason}</p>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500">Spent so far</p>
              <p className="text-lg font-semibold text-slate-900">{format(forecast.spent_so_far)}</p>
              <p className="text-xs text-slate-500">
                Day {forecast.elapsed_days} of {forecast.days_in_month}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Projected by month end</p>
              <p className="text-lg font-semibold text-slate-900">{format(forecast.projected_expense)}</p>
              <p className="text-xs text-slate-500">Based on this month and the last 3</p>
            </div>
          </div>

          {forecast.budget_warnings.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-800">Budgets likely to go over</h3>
              <ul className="space-y-2">
                {forecast.budget_warnings.map((w) => (
                  <li key={w.category_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: w.color }} aria-hidden="true" />
                      {w.name}
                    </span>
                    <span className="flex items-center gap-2 text-slate-600">
                      {format(w.projected)} of {format(w.budget)}
                      {w.projected_status && <StatusBadge status={w.projected_status} />}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {forecast.goals.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-800">Savings goals at your current pace</h3>
              <ul className="space-y-2">
                {forecast.goals.map((g) => (
                  <li key={g.goal_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span>{g.name}</span>
                    <span className="text-slate-600">
                      {g.projected_completion ? (
                        <>
                          Reached around {formatDate(g.projected_completion)}
                          {g.on_track === true && <span className="ml-1 text-[#086b08]">(on track)</span>}
                          {g.on_track === false && <span className="ml-1 text-[#a32727]">(after target date)</span>}
                        </>
                      ) : (
                        "No progress yet"
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
