import { aiApi } from "../../api/ai";
import { useApi } from "../../hooks/useApi";
import type { Insight } from "../../types";
import { ErrorAlert } from "../common/Feedback";
import { Icon, type IconName } from "../common/Icon";
import { Spinner } from "../common/Spinner";

const TONE: Record<Insight["tone"], { icon: IconName; className: string; label: string }> = {
  positive: { icon: "check", className: "bg-good/10 text-[#086b08]", label: "Good news" },
  neutral: { icon: "sparkles", className: "bg-income/10 text-[#1d5aa3]", label: "Observation" },
  warning: { icon: "alert", className: "bg-warning/20 text-[#8a5a00]", label: "Needs attention" },
};

/**
 * SW-13: observations for a month, worked out by SpendWise's own rules.
 * Every insight shows the figures it's based on.
 */
export function InsightsCard({ month, refreshKey }: { month: string; refreshKey?: unknown }) {
  const { data, loading, error, reload } = useApi(() => aiApi.insights(month), [month, refreshKey]);

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <Icon name="sparkles" className="h-5 w-5 text-brand-700" /> Insights
        </h2>
        {loading && <Spinner className="h-4 w-4" />}
      </div>

      <ErrorAlert message={error} onRetry={reload} />
      {data && !data.available && <p className="text-sm text-slate-500">{data.reason}</p>}
      {data?.available && data.insights.length === 0 && <p className="text-sm text-slate-500">Nothing stands out this month.</p>}
      {data?.available && data.insights.length > 0 && (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.insights.map((insight, i) => {
            const tone = TONE[insight.tone];
            return (
              <li key={i} className="rounded-lg border border-slate-200 p-4">
                <div className="mb-2 flex items-start gap-2">
                  <span className={`mt-0.5 inline-flex shrink-0 items-center rounded-full p-1 ${tone.className}`} title={tone.label}>
                    <Icon name={tone.icon} className="h-3.5 w-3.5" />
                    <span className="sr-only">{tone.label}</span>
                  </span>
                  <h3 className="text-sm font-semibold text-slate-900">{insight.title}</h3>
                </div>
                <p className="text-sm text-slate-700">{insight.body}</p>
                <details className="mt-3 text-xs text-slate-500">
                  <summary className="cursor-pointer select-none hover:text-slate-700">Based on</summary>
                  <ul className="mt-1 space-y-0.5">
                    {insight.facts.map((f) => (
                      <li key={f.id}>
                        {f.label}: <span className="font-medium text-slate-700">{f.value}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
