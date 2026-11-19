import type { MonthTotals } from "../../types";
import { formatPercent, toNumber } from "../../utils/currency";
import { Icon } from "../common/Icon";

interface StatCardProps {
  label: string;
  value: string;
  accent?: string;
  change?: string | null;
  /** true when an increase is good (income), false when it's bad (expenses). */
  increaseIsGood?: boolean;
  hint?: string;
}

export function StatCard({ label, value, accent, change, increaseIsGood = true, hint }: StatCardProps) {
  const n = change === null || change === undefined ? null : toNumber(change);
  const good = n === null ? null : increaseIsGood ? n >= 0 : n <= 0;
  return (
    <div className="card">
      <div className="flex items-center gap-2">
        {accent && <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: accent }} aria-hidden="true" />}
        <p className="text-sm font-medium text-slate-500">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      {n !== null ? (
        <p className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${good ? "text-[#086b08]" : "text-[#a32727]"}`}>
          <Icon name={n >= 0 ? "arrowUp" : "arrowDown"} className="h-3 w-3" />
          {formatPercent(Math.abs(n))} vs last month
        </p>
      ) : (
        hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>
      )}
    </div>
  );
}

interface SummaryCardsProps {
  totals: MonthTotals;
  incomeChange: string | null;
  expenseChange: string | null;
  format: (value: string | number) => string;
}

export function SummaryCards({ totals, incomeChange, expenseChange, format }: SummaryCardsProps) {
  const net = toNumber(totals.net);
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Income" value={format(totals.income)} accent="#2a78d6" change={incomeChange} hint="No data last month" />
      <StatCard label="Expenses" value={format(totals.expense)} accent="#eb6834" change={expenseChange} increaseIsGood={false} hint="No data last month" />
      <StatCard label="Net balance" value={format(totals.net)} hint={net >= 0 ? "You spent less than you earned" : "You spent more than you earned"} />
      <StatCard label="Savings rate" value={formatPercent(totals.savings_rate)} hint={`${totals.transaction_count} transactions this month`} />
    </div>
  );
}
