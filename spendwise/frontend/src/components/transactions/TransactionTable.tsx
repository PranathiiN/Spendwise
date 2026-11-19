import { PAYMENT_METHOD_LABELS, type Transaction, type TransactionFilters } from "../../types";
import { formatDate } from "../../utils/dates";
import { CategoryDot } from "../common/CategoryDot";
import { Icon } from "../common/Icon";
import { TransactionAmount } from "../dashboard/RecentTransactions";

interface Props {
  items: Transaction[];
  format: (v: string) => string;
  sortBy: TransactionFilters["sort_by"];
  sortOrder: TransactionFilters["sort_order"];
  onSort: (column: NonNullable<TransactionFilters["sort_by"]>) => void;
  onEdit: (tx: Transaction) => void;
  onDelete: (tx: Transaction) => void;
}

function SortHeader({
  label,
  column,
  sortBy,
  sortOrder,
  onSort,
  align = "left",
}: {
  label: string;
  column: NonNullable<TransactionFilters["sort_by"]>;
  sortBy: Props["sortBy"];
  sortOrder: Props["sortOrder"];
  onSort: Props["onSort"];
  align?: "left" | "right";
}) {
  const active = sortBy === column;
  return (
    <th className={`px-4 py-3 font-medium ${align === "right" ? "text-right" : "text-left"}`} aria-sort={active ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="inline-flex items-center gap-1 hover:text-slate-900" onClick={() => onSort(column)}>
        {label}
        {active && <Icon name={sortOrder === "asc" ? "arrowUp" : "arrowDown"} className="h-3 w-3" />}
      </button>
    </th>
  );
}

export function TransactionTable({ items, format, sortBy, sortOrder, onSort, onEdit, onDelete }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-xs tracking-wide text-slate-500 uppercase">
          <tr>
            <SortHeader label="Date" column="transaction_date" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
            <SortHeader label="Description" column="description" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} />
            <th className="px-4 py-3 text-left font-medium">Category</th>
            <th className="hidden px-4 py-3 text-left font-medium md:table-cell">Payment</th>
            <SortHeader label="Amount" column="amount" sortBy={sortBy} sortOrder={sortOrder} onSort={onSort} align="right" />
            <th className="px-4 py-3"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((tx) => (
            <tr key={tx.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">{formatDate(tx.transaction_date)}</td>
              <td className="max-w-xs px-4 py-3">
                <p className="truncate font-medium text-slate-900">{tx.description}</p>
                {tx.notes && <p className="truncate text-xs text-slate-500">{tx.notes}</p>}
              </td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center gap-2 whitespace-nowrap">
                  <CategoryDot color={tx.category.color} name={tx.category.name} size="sm" />
                  {tx.category.name}
                </span>
              </td>
              <td className="hidden px-4 py-3 whitespace-nowrap text-slate-600 md:table-cell">
                {tx.payment_method ? PAYMENT_METHOD_LABELS[tx.payment_method] : "-"}
              </td>
              <td className="px-4 py-3 text-right whitespace-nowrap">
                <TransactionAmount tx={tx} format={format} />
              </td>
              <td className="px-4 py-3 text-right whitespace-nowrap">
                <button type="button" className="btn-ghost" onClick={() => onEdit(tx)} aria-label={`Edit ${tx.description}`}>
                  <Icon name="edit" className="h-4 w-4" />
                </button>
                <button type="button" className="btn-ghost hover:text-critical" onClick={() => onDelete(tx)} aria-label={`Delete ${tx.description}`}>
                  <Icon name="trash" className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
