import { formatMonthLabel, shiftMonth } from "../../utils/dates";
import { Icon } from "./Icon";

export function MonthPicker({ value, onChange }: { value: string; onChange: (month: string) => void }) {
  return (
    <div className="inline-flex items-center rounded-lg border border-slate-300 bg-white shadow-sm">
      <button type="button" className="rounded-l-lg px-2 py-2 text-slate-600 hover:bg-slate-50" onClick={() => onChange(shiftMonth(value, -1))} aria-label="Previous month">
        <Icon name="chevronLeft" className="h-4 w-4" />
      </button>
      <label className="relative px-2 text-sm font-medium text-slate-800">
        <span className="pointer-events-none">{formatMonthLabel(value)}</span>
        <input
          type="month"
          value={value}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          className="absolute inset-0 cursor-pointer opacity-0"
          aria-label="Choose month"
        />
      </label>
      <button type="button" className="rounded-r-lg px-2 py-2 text-slate-600 hover:bg-slate-50" onClick={() => onChange(shiftMonth(value, 1))} aria-label="Next month">
        <Icon name="chevronRight" className="h-4 w-4" />
      </button>
    </div>
  );
}
