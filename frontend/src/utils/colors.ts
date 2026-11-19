// Chart colors (validated categorical slots) and reserved status colors.
export const SERIES_COLORS = {
  income: "#2a78d6",
  expense: "#eb6834",
} as const;

export const STATUS_COLORS = {
  ok: "#0ca30c",
  warning: "#fab219",
  exceeded: "#d03b3b",
} as const;

export const CHART_INK = {
  axis: "#52514e",
  grid: "#e7e5e4",
} as const;

// Palette offered when creating custom categories / goals.
export const PICKER_COLORS = [
  "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
  "#008300", "#6250d6", "#e34948", "#0d9488", "#64748b",
];
