import { useState } from "react";
import { getErrorMessage } from "../api/client";
import { reportsApi } from "../api/reports";
import { ErrorAlert, PageHeader } from "../components/common/Feedback";
import { Icon } from "../components/common/Icon";
import { MonthPicker } from "../components/common/MonthPicker";
import { PageLoader } from "../components/common/Spinner";
import { StatusBadge } from "../components/common/StatusBadge";
import { CategoryDonut } from "../components/dashboard/CategoryDonut";
import { CategoryTable } from "../components/dashboard/CategoryTable";
import { DailySpendingChart } from "../components/dashboard/DailySpendingChart";
import { TransactionAmount } from "../components/dashboard/RecentTransactions";
import { StatCard } from "../components/dashboard/SummaryCards";
import { TrendChart } from "../components/dashboard/TrendChart";
import { useApi } from "../hooks/useApi";
import { useCurrency } from "../hooks/useCurrency";
import { formatPercent, toNumber } from "../utils/currency";
import { currentMonth, formatDate } from "../utils/dates";

export function ReportsPage() {
  const { format } = useCurrency();
  const [month, setMonth] = useState(currentMonth());
  const { data, loading, error, reload } = useApi(() => reportsApi.monthly(month), [month]);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await reportsApi.downloadCsv(month);
    } catch (err) {
      setExportError(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Monthly report"
        subtitle={data ? data.label : "Your month at a glance"}
        actions={
          <>
            <MonthPicker value={month} onChange={setMonth} />
            <button type="button" className="btn-secondary" onClick={handleExport} disabled={exporting}>
              <Icon name="download" className="h-4 w-4" /> {exporting ? "Exporting..." : "Export CSV"}
            </button>
          </>
        }
      />

      <ErrorAlert message={exportError} />
      <ErrorAlert message={error} onRetry={reload} />

      {loading && !data ? (
        <PageLoader />
      ) : data ? (
        <div className={`space-y-6 ${loading ? "opacity-60" : ""}`}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Income" accent="#2a78d6" value={format(data.totals.income)} change={data.income_change_percent} hint="No data last month" />
            <StatCard label="Expenses" accent="#eb6834" value={format(data.totals.expense)} change={data.expense_change_percent} increaseIsGood={false} hint="No data last month" />
            <StatCard
              label="Net savings"
              value={format(data.totals.net)}
              hint={`Savings rate ${formatPercent(data.totals.savings_rate)}`}
            />
            <StatCard
              label="Average daily spend"
              value={format(data.average_daily_expense)}
              hint={
                data.highest_expense_day
                  ? `Highest: ${format(data.highest_expense_day.expense)} on ${formatDate(data.highest_expense_day.date)}`
                  : "No expenses this month"
              }
            />
          </div>

          <div className="card">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Daily spending</h2>
            {toNumber(data.totals.expense) === 0 ? (
              <p className="py-10 text-center text-sm text-slate-500">No expenses recorded this month.</p>
            ) : (
              <DailySpendingChart data={data.daily} format={format} />
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <div className="card">
              <h2 className="mb-4 text-base font-semibold text-slate-900">Expenses by category</h2>
              <CategoryDonut items={data.expense_by_category} format={format} />
              <div className="mt-6 border-t border-slate-100 pt-4">
                <CategoryTable items={data.expense_by_category} format={format} emptyText="No expenses this month." />
              </div>
            </div>
            <div className="space-y-6">
              <div className="card">
                <h2 className="mb-4 text-base font-semibold text-slate-900">Income by category</h2>
                <CategoryTable items={data.income_by_category} format={format} emptyText="No income this month." />
              </div>
              <div className="card">
                <h2 className="mb-4 text-base font-semibold text-slate-900">Top expenses</h2>
                {data.top_expenses.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-500">No expenses this month.</p>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {data.top_expenses.map((tx) => (
                      <li key={tx.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                        <div className="min-w-0">
                          <p className="truncate font-medium text-slate-900">{tx.description}</p>
                          <p className="text-xs text-slate-500">
                            {tx.category.name} · {formatDate(tx.transaction_date)}
                          </p>
                        </div>
                        <TransactionAmount tx={tx} format={format} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Budget performance</h2>
            {data.budgets.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">No budgets were set for this month.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs text-slate-500 uppercase">
                    <tr>
                      <th className="pb-2 font-medium">Category</th>
                      <th className="pb-2 text-right font-medium">Budget</th>
                      <th className="pb-2 text-right font-medium">Spent</th>
                      <th className="pb-2 text-right font-medium">Remaining</th>
                      <th className="pb-2 text-right font-medium">Used</th>
                      <th className="pb-2 pl-4 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.budgets.map((b) => (
                      <tr key={b.id}>
                        <td className="py-2.5 text-slate-800">{b.category.name}</td>
                        <td className="py-2.5 text-right tabular-nums">{format(b.amount)}</td>
                        <td className="py-2.5 text-right tabular-nums">{format(b.spent)}</td>
                        <td className={`py-2.5 text-right tabular-nums ${toNumber(b.remaining) < 0 ? "text-[#a32727]" : ""}`}>
                          {format(b.remaining)}
                        </td>
                        <td className="py-2.5 text-right tabular-nums">{formatPercent(b.percent_used)}</td>
                        <td className="py-2.5 pl-4"><StatusBadge status={b.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Six-month trend</h2>
            <TrendChart data={data.six_month_trend} format={format} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
