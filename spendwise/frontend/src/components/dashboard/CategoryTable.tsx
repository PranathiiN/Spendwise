import type { CategoryBreakdownItem } from "../../types";
import { formatPercent } from "../../utils/currency";
import { ProgressBar } from "../common/ProgressBar";

interface CategoryTableProps {
  items: CategoryBreakdownItem[];
  format: (v: string) => string;
  emptyText: string;
}

/** Tabular view of a category breakdown (doubles as the accessible table view for charts). */
export function CategoryTable({ items, format, emptyText }: CategoryTableProps) {
  if (items.length === 0) return <p className="py-6 text-center text-sm text-slate-500">{emptyText}</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs text-slate-500 uppercase">
        <tr>
          <th className="pb-2 font-medium">Category</th>
          <th className="pb-2 text-right font-medium">Amount</th>
          <th className="hidden pb-2 pl-4 font-medium sm:table-cell">Share</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {items.map((item) => (
          <tr key={item.category_id}>
            <td className="py-2.5">
              <span className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
                <span className="text-slate-800">{item.name}</span>
                <span className="text-xs text-slate-400">({item.transaction_count})</span>
              </span>
            </td>
            <td className="py-2.5 text-right font-medium whitespace-nowrap text-slate-900 tabular-nums">{format(item.amount)}</td>
            <td className="hidden w-1/3 py-2.5 pl-4 sm:table-cell">
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <ProgressBar percent={item.percent} color={item.color} label={`${item.name} share`} />
                </div>
                <span className="w-12 text-right text-xs text-slate-500">{formatPercent(item.percent)}</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
