import { useEffect, useState } from "react";
import { aiApi } from "../../api/ai";
import { getErrorMessage } from "../../api/client";
import { useAiStatus } from "../../hooks/useAiStatus";
import type { Insight, InsightsResponse } from "../../types";
import { ErrorAlert } from "../common/Feedback";
import { Icon, type IconName } from "../common/Icon";
import { Spinner } from "../common/Spinner";

const TONE: Record<Insight["tone"], { icon: IconName; className: string; label: string }> = {
  positive: { icon: "check", className: "bg-good/10 text-[#086b08]", label: "Good news" },
  neutral: { icon: "sparkles", className: "bg-income/10 text-[#1d5aa3]", label: "Observation" },
  warning: { icon: "alert", className: "bg-warning/20 text-[#8a5a00]", label: "Needs attention" },
};

/** SW-13: AI-written observations for a month. Every insight shows the figures it's based on. */
export function InsightsCard({ month }: { month: string }) {
  const ai = useAiStatus();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Insights belong to one month; reset when it changes.
  useEffect(() => {
    setData(null);
    setError(null);
  }, [month]);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await aiApi.insights(month));
    } catch (err) {
      setError(getErrorMessage(err, "Couldn't generate insights."));
    } finally {
      setLoading(false);
    }
  };

  if (ai === null) return null;

  return (
    <div className="card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <Icon name="sparkles" className="h-5 w-5 text-brand-700" /> Insights
        </h2>
        {ai.enabled && (
          <button type="button" className="btn-secondary" onClick={generate} disabled={loading}>
            {loading ? <Spinner className="h-4 w-4" /> : <Icon name="sparkles" className="h-4 w-4" />}
            {loading ? "Thinking..." : data ? "Refresh" : "Generate insights"}
          </button>
        )}
      </div>

      {!ai.enabled ? (
        <p className="text-sm text-slate-500">
          AI insights are switched off. Add an <code className="rounded bg-slate-100 px-1">ANTHROPIC_API_KEY</code> to{" "}
          <code className="rounded bg-slate-100 px-1">backend/.env</code> and restart the backend to turn them on.
        </p>
      ) : (
        <>
          <ErrorAlert message={error} />
          {!data && !loading && !error && (
            <p className="text-sm text-slate-500">
              Get plain-language observations about this month: big changes, unusual spending, budgets and goals.
            </p>
          )}
          {data && !data.available && <p className="text-sm text-slate-500">{data.reason}</p>}
          {data?.available && data.insights.length === 0 && (
            <p className="text-sm text-slate-500">Nothing stands out this month.</p>
          )}
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
        </>
      )}
    </div>
  );
}
