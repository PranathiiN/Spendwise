import { useState } from "react";
import { Link } from "react-router";
import { dashboardApi } from "../api/dashboard";
import { EmptyState, ErrorAlert, PageHeader } from "../components/common/Feedback";
import { MonthPicker } from "../components/common/MonthPicker";
import { PageLoader } from "../components/common/Spinner";
import { BudgetAlerts } from "../components/dashboard/BudgetAlerts";
import { CategoryDonut } from "../components/dashboard/CategoryDonut";
import { GoalsOverview } from "../components/dashboard/GoalsOverview";
import { RecentTransactions } from "../components/dashboard/RecentTransactions";
import { SummaryCards } from "../components/dashboard/SummaryCards";
import { TrendChart } from "../components/dashboard/TrendChart";
import { useAuth } from "../contexts/AuthContext";
import { useApi } from "../hooks/useApi";
import { useCurrency } from "../hooks/useCurrency";
import { currentMonth } from "../utils/dates";

export function DashboardPage() {
  const { user } = useAuth();
  const { format } = useCurrency();
  const [month, setMonth] = useState(currentMonth());
  const { data, loading, error, reload } = useApi(() => dashboardApi.get(month), [month]);

  const firstName = user?.name.split(" ")[0] ?? "";
  const hasAnyData = data ? data.recent_transactions.length > 0 : false;

  return (
    <div>
      <PageHeader
        title={`Hello, ${firstName}`}
        subtitle="Here is your financial overview"
        actions={<MonthPicker value={month} onChange={setMonth} />}
      />
      <ErrorAlert message={error} onRetry={reload} />

      {loading && !data ? (
        <PageLoader />
      ) : data ? (
        !hasAnyData ? (
          <EmptyState
            title="Welcome to SpendWise"
            description="Add your first income or expense to see your dashboard come alive."
            action={<Link to="/transactions" className="btn-primary">Add a transaction</Link>}
          />
        ) : (
          <div className={`space-y-6 ${loading ? "opacity-60" : ""}`}>
            <SummaryCards
              totals={data.totals}
              incomeChange={data.income_change_percent}
              expenseChange={data.expense_change_percent}
              format={format}
            />

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <div className="card xl:col-span-3">
                <h2 className="mb-4 text-base font-semibold text-slate-900">Income vs expenses (last 6 months)</h2>
                <TrendChart data={data.monthly_trend} format={format} />
              </div>
              <div className="card xl:col-span-2">
                <h2 className="mb-4 text-base font-semibold text-slate-900">Spending by category</h2>
                <CategoryDonut items={data.expense_by_category} format={format} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <RecentTransactions items={data.recent_transactions} format={format} />
              <BudgetAlerts alerts={data.budget_alerts} budgetCount={data.budget_summary.budget_count} format={format} />
              <GoalsOverview goals={data.goals} summary={data.goals_summary} format={format} />
            </div>
          </div>
        )
      ) : null}
    </div>
  );
}
