import { Link } from "react-router";
import type { Transaction } from "../../types";
import { formatDate } from "../../utils/dates";
import { CategoryDot } from "../common/CategoryDot";

export function TransactionAmount({ tx, format }: { tx: Transaction; format: (v: string) => string }) {
  const isIncome = tx.transaction_type === "income";
  return (
    <span className={`font-semibold tabular-nums ${isIncome ? "text-[#1d5aa3]" : "text-slate-900"}`}>
      {isIncome ? "+" : "-"}
      {format(tx.amount)}
    </span>
  );
}

export function RecentTransactions({ items, format }: { items: Transaction[]; format: (v: string) => string }) {
  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Recent transactions</h2>
        <Link to="/transactions" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">No transactions yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((tx) => (
            <li key={tx.id} className="flex items-center gap-3 py-3">
              <CategoryDot color={tx.category.color} name={tx.category.name} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-900">{tx.description}</p>
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
  );
}
