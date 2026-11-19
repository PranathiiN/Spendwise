import { PAYMENT_METHOD_LABELS, type Category, type TransactionFilters } from "../../types";
import { Icon } from "../common/Icon";

interface Props {
  filters: TransactionFilters;
  searchText: string;
  onSearchChange: (text: string) => void;
  onChange: (patch: Partial<TransactionFilters>) => void;
  onReset: () => void;
  categories: Category[];
}

export function TransactionFiltersBar({ filters, searchText, onSearchChange, onChange, onReset, categories }: Props) {
  const visibleCategories = filters.transaction_type
    ? categories.filter((c) => c.transaction_type === filters.transaction_type)
    : categories;

  return (
    <div className="card space-y-3 p-4">
      <div className="flex flex-col gap-3 md:flex-row">
        <div className="relative flex-1">
          <Icon name="search" className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-slate-400" />
          <input
            type="search"
            value={searchText}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search description or notes"
            className="input pl-9"
            aria-label="Search transactions"
          />
        </div>
        <select
          className="input md:w-40"
          value={filters.transaction_type ?? ""}
          onChange={(e) => onChange({ transaction_type: e.target.value as TransactionFilters["transaction_type"], category_id: "" })}
          aria-label="Type"
        >
          <option value="">All types</option>
          <option value="expense">Expenses</option>
          <option value="income">Income</option>
        </select>
        <select
          className="input md:w-52"
          value={filters.category_id ?? ""}
          onChange={(e) => onChange({ category_id: e.target.value })}
          aria-label="Category"
        >
          <option value="">All categories</option>
          {visibleCategories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
              {filters.transaction_type ? "" : ` (${c.transaction_type})`}
            </option>
          ))}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        <div>
          <label className="mb-1 block text-xs text-slate-500" htmlFor="f-start">From</label>
          <input id="f-start" type="date" className="input" value={filters.start_date ?? ""} onChange={(e) => onChange({ start_date: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500" htmlFor="f-end">To</label>
          <input id="f-end" type="date" className="input" value={filters.end_date ?? ""} onChange={(e) => onChange({ end_date: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500" htmlFor="f-min">Min amount</label>
          <input id="f-min" inputMode="decimal" className="input" value={filters.min_amount ?? ""} onChange={(e) => onChange({ min_amount: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500" htmlFor="f-max">Max amount</label>
          <input id="f-max" inputMode="decimal" className="input" value={filters.max_amount ?? ""} onChange={(e) => onChange({ max_amount: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500" htmlFor="f-pm">Payment</label>
          <select id="f-pm" className="input" value={filters.payment_method ?? ""} onChange={(e) => onChange({ payment_method: e.target.value as TransactionFilters["payment_method"] })}>
            <option value="">Any</option>
            {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <button type="button" className="btn-secondary w-full" onClick={onReset}>Reset filters</button>
        </div>
      </div>
    </div>
  );
}
