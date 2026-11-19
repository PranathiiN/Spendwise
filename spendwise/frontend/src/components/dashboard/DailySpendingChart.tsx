import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DailyPoint } from "../../types";
import { CHART_INK, SERIES_COLORS } from "../../utils/colors";
import { toNumber } from "../../utils/currency";
import { formatDate } from "../../utils/dates";

interface DailySpendingChartProps {
  data: DailyPoint[];
  format: (value: string | number, compact?: boolean) => string;
}

/** Single series (daily expenses) - the card title names it, so no legend box. */
export function DailySpendingChart({ data, format }: DailySpendingChartProps) {
  const chartData = data.map((p) => ({
    day: Number(p.date.slice(8, 10)),
    date: p.date,
    expense: toNumber(p.expense),
  }));

  return (
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer>
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={CHART_INK.grid} />
          <XAxis dataKey="day" tickLine={false} axisLine={false} interval="preserveStartEnd" tick={{ fill: CHART_INK.axis, fontSize: 12 }} />
          <YAxis tickLine={false} axisLine={false} width={64} tick={{ fill: CHART_INK.axis, fontSize: 12 }} tickFormatter={(v) => format(Number(v), true)} />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.12)" }}
            labelFormatter={(_label, payload) => {
              const first = payload?.[0]?.payload as { date?: string } | undefined;
              return first?.date ? formatDate(first.date) : "";
            }}
            formatter={(value) => [format(Number(value)), "Spent"]}
            contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 13 }}
          />
          <Bar dataKey="expense" fill={SERIES_COLORS.expense} radius={[4, 4, 0, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
