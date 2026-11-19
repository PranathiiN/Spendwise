const formatterCache = new Map<string, Intl.NumberFormat>();

function localeFor(currency: string): string | undefined {
  // Indian digit grouping (1,00,000) for INR; browser default otherwise.
  return currency === "INR" ? "en-IN" : undefined;
}

function getFormatter(currency: string, compact: boolean): Intl.NumberFormat {
  const key = `${currency}|${compact}`;
  let fmt = formatterCache.get(key);
  if (!fmt) {
    fmt = new Intl.NumberFormat(localeFor(currency), {
      style: "currency",
      currency,
      notation: compact ? "compact" : "standard",
      minimumFractionDigits: compact ? 0 : 2,
      maximumFractionDigits: compact ? 1 : 2,
    });
    formatterCache.set(key, fmt);
  }
  return fmt;
}

/** Parse an API decimal string for DISPLAY or charting only. Never send the result back. */
export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function formatCurrency(
  value: string | number | null | undefined,
  currency = "INR",
  options: { compact?: boolean } = {},
): string {
  return getFormatter(currency, options.compact ?? false).format(toNumber(value));
}

export function formatPercent(value: string | number | null | undefined, withSign = false): string {
  const n = toNumber(value);
  const sign = withSign && n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}
