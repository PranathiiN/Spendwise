import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { CategoryBreakdownItem } from "../../types";
import { formatPercent, toNumber } from "../../utils/currency";

interface CategoryDonutProps {
  items: CategoryBreakdownItem[];
  format: (value: string | number) => string;
  emptyText?: string;
}

const MAX_SLICES = 7;

/**
 * Donut of spending by category. Each slice keeps its category's own color, small
 * categories fold into "Other", and the list beside it carries names and values
 * so identity never depends on color alone.
 */
export function CategoryDonut({ items, format, emptyText = "No expenses recorded this month." }: CategoryDonutProps) {
  if (items.length === 0) {
    return <p className="py-12 text-center text-sm text-slate-500">{emptyText}</p>;
  }

  const head = items.slice(0, MAX_SLICES);
  const tail = items.slice(MAX_SLICES);
  const slices = head.map((i) => ({ name: i.name, value: toNumber(i.amount), color: i.color, percent: i.percent }));
  if (tail.length > 0) {
    const otherValue = tail.reduce((sum, i) => sum + toNumber(i.amount), 0);
    const otherPct = tail.reduce((sum, i) => sum + toNumber(i.percent), 0);
    slices.push({ name: `Other (${tail.length})`, value: otherValue, color: "#94a3b8", percent: otherPct.toFixed(1) });
  }

  return (
    <div className="flex flex-col items-center gap-4 md:flex-row">
      <div className="h-52 w-52 shrink-0">
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              innerRadius="60%"
              outerRadius="100%"
              paddingAngle={1}
              stroke="#ffffff"
              strokeWidth={2}
              isAnimationActive={false}
            >
              {slices.map((s) => (
                <Cell key={s.name} fill={s.color} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => format(Number(value))} contentStyle={{ borderRadius: 8, fontSize: 13 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-2">
        {slices.map((s) => (
          <li key={s.name} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex min-w-0 items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: s.color }} aria-hidden="true" />
              <span className="truncate text-slate-700">{s.name}</span>
            </span>
            <span className="shrink-0 text-right">
              <span className="font-medium text-slate-900">{format(s.value)}</span>
              <span className="ml-2 text-xs text-slate-500">{formatPercent(s.percent)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
