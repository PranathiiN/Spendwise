import type { ReactNode } from "react";
import { Icon } from "./Icon";

export function ErrorAlert({ message, onRetry }: { message: string | null; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div className="flex items-start gap-3 rounded-lg border border-critical/30 bg-critical/5 px-4 py-3 text-sm text-slate-800" role="alert">
      <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button type="button" className="font-medium text-brand-700 hover:underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function SuccessAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 rounded-lg border border-good/30 bg-good/5 px-4 py-3 text-sm text-slate-800" role="status">
      <Icon name="check" className="h-4 w-4 text-good" />
      {message}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
