import { toNumber } from "../../utils/currency";

interface ProgressBarProps {
  percent: string | number;
  color: string;
  /** Optional marker (0-100) e.g. a budget alert threshold. */
  marker?: number;
  label?: string;
}

export function ProgressBar({ percent, color, marker, label }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, toNumber(percent)));
  return (
    <div
      className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      {marker !== undefined && marker < 100 && (
        <div className="absolute top-0 h-full w-0.5 bg-slate-500/60" style={{ left: `${marker}%` }} title={`Alert at ${marker}%`} />
      )}
    </div>
  );
}
