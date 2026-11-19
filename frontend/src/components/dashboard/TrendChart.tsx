import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TrendPoint } from "../../types";
import { CHART_INK, SERIES_COLORS } from "../../utils/colors";
import { toNumber } from "../../utils/currency";

interface TrendChartProps {
  data: TrendPoint[];
  format: (value: string | number, compact?: boolean) => string;
  height?: number;
  /** SW-15: projected month-end spending for one month, drawn as an outlined bar. */
  projected?: { month: string; expense: string } | null;
}

const PROJECTED_KEY = "Projected expenses (estimate)";

/** Income vs expenses per month - grouped bars on a single shared axis. */
export function TrendChart({ data, format, height = 280, projected }: TrendChartProps) {
  const chartData = data.map((p) => ({
    label: p.label,
    Income: toNumber(p.income),
    Expenses: toNumber(p.expense),
    ...(projected && projected.month === p.month ? { [PROJECTED_KEY]: toNumber(projected.expense) } : {}),
  }));
  const showProjected = Boolean(projected && data.some((p) => p.month === projected.month));

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={chartData} barGap={2} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={CHART_INK.grid} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: CHART_INK.axis, fontSize: 12 }} />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={64}
            tick={{ fill: CHART_INK.axis, fontSize: 12 }}
            tickFormatter={(v) => format(Number(v), true)}
          />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.12)" }}
            formatter={(value) => format(Number(value))}
            contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 13 }}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: CHART_INK.axis }} />
          <Bar dataKey="Income" fill={SERIES_COLORS.income} radius={[4, 4, 0, 0]} maxBarSize={28} />
          <Bar dataKey="Expenses" fill={SERIES_COLORS.expense} radius={[4, 4, 0, 0]} maxBarSize={28} />
          {showProjected && (
            <Bar
              dataKey={PROJECTED_KEY}
              fill="#ffffff"
              stroke={SERIES_COLORS.expense}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              radius={[4, 4, 0, 0]}
              maxBarSize={28}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
