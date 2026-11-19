// Monetary values arrive from the API as decimal STRINGS (e.g. "1234.50") so no
// precision is lost. Convert to number only for display/charting.
export type Money = string;

export type TransactionType = "income" | "expense";
export type BudgetStatus = "ok" | "warning" | "exceeded";
export type GoalStatus = "active" | "completed" | "overdue";

export type PaymentMethod =
  | "cash"
  | "upi"
  | "debit_card"
  | "credit_card"
  | "net_banking"
  | "bank_transfer"
  | "wallet"
  | "cheque"
  | "other";

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash: "Cash",
  upi: "UPI",
  debit_card: "Debit card",
  credit_card: "Credit card",
  net_banking: "Net banking",
  bank_transfer: "Bank transfer",
  wallet: "Wallet",
  cheque: "Cheque",
  other: "Other",
};

export const SUPPORTED_CURRENCIES = [
  "INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "AED", "CHF", "CNY", "NZD", "ZAR",
] as const;

export interface User {
  id: string;
  name: string;
  email: string;
  preferred_currency: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Category {
  id: string;
  name: string;
  transaction_type: TransactionType;
  color: string;
  icon_name: string;
  is_system: boolean;
  created_at: string;
}

export interface Transaction {
  id: string;
  category_id: string;
  category: Category;
  description: string;
  amount: Money;
  transaction_type: TransactionType;
  transaction_date: string; // YYYY-MM-DD
  payment_method: PaymentMethod | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionPayload {
  category_id: string;
  description: string;
  amount: Money;
  transaction_type: TransactionType;
  transaction_date: string;
  payment_method: PaymentMethod | null;
  notes: string | null;
}

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  search?: string;
  transaction_type?: TransactionType | "";
  category_id?: string;
  payment_method?: PaymentMethod | "";
  start_date?: string;
  end_date?: string;
  min_amount?: string;
  max_amount?: string;
  sort_by?: "transaction_date" | "amount" | "description" | "created_at";
  sort_order?: "asc" | "desc";
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  total_income: Money;
  total_expense: Money;
}

export interface Budget {
  id: string;
  category: Category;
  month: string; // YYYY-MM
  amount: Money;
  alert_threshold: number;
  spent: Money;
  remaining: Money;
  percent_used: string;
  status: BudgetStatus;
  created_at: string;
  updated_at: string;
}

export interface BudgetListResponse {
  month: string;
  budgets: Budget[];
  total_budgeted: Money;
  total_spent: Money;
  total_remaining: Money;
  warning_count: number;
  exceeded_count: number;
}

export interface SavingsGoal {
  id: string;
  name: string;
  target_amount: Money;
  current_amount: Money;
  remaining_amount: Money;
  progress_percent: string;
  target_date: string | null;
  days_remaining: number | null;
  monthly_required: Money | null;
  status: GoalStatus;
  is_completed: boolean;
  color: string;
  icon_name: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SavingsGoalPayload {
  name: string;
  target_amount: Money;
  current_amount?: Money;
  target_date: string | null;
  color: string;
  notes: string | null;
}

export interface MonthTotals {
  income: Money;
  expense: Money;
  net: Money;
  savings_rate: string;
  transaction_count: number;
}

export interface CategoryBreakdownItem {
  category_id: string;
  name: string;
  color: string;
  icon_name: string;
  amount: Money;
  percent: string;
  transaction_count: number;
}

export interface TrendPoint {
  month: string;
  label: string;
  income: Money;
  expense: Money;
  net: Money;
}

export interface DashboardData {
  month: string;
  currency: string;
  totals: MonthTotals;
  previous_totals: MonthTotals;
  income_change_percent: string | null;
  expense_change_percent: string | null;
  expense_by_category: CategoryBreakdownItem[];
  monthly_trend: TrendPoint[];
  recent_transactions: Transaction[];
  budget_alerts: Budget[];
  budget_summary: {
    total_budgeted: Money;
    total_spent: Money;
    budget_count: number;
    warning_count: number;
    exceeded_count: number;
  };
  goals: SavingsGoal[];
  goals_summary: {
    active_count: number;
    completed_count: number;
    total_saved: Money;
    total_target: Money;
  };
}

export interface DailyPoint {
  date: string;
  income: Money;
  expense: Money;
  cumulative_expense: Money;
}

export interface MonthlyReport {
  month: string;
  label: string;
  currency: string;
  totals: MonthTotals;
  previous_totals: MonthTotals;
  income_change_percent: string | null;
  expense_change_percent: string | null;
  income_by_category: CategoryBreakdownItem[];
  expense_by_category: CategoryBreakdownItem[];
  daily: DailyPoint[];
  top_expenses: Transaction[];
  budgets: Budget[];
  average_daily_expense: Money;
  highest_expense_day: DailyPoint | null;
  six_month_trend: TrendPoint[];
}

// ---- Phase 2 AI features ----------------------------------------------------------

export interface AIStatus {
  /** SpendWise's own models (categories, quick add, insights, assistant) - always on. */
  enabled: boolean;
  /** Receipt scanning needs an optional LLM provider (Ollama or Claude). */
  receipt_scanning: boolean;
  provider: "ollama" | "anthropic" | "off";
  model: string | null;
  /** Why receipt scanning is unavailable, if it is. */
  message: string | null;
}

export interface ParsedTransaction {
  transaction_type: TransactionType;
  amount: Money | null;
  description: string;
  transaction_date: string | null;
  category: Category | null;
  payment_method: PaymentMethod | null;
  missing: string[];
}

export interface CategorySuggestion {
  category: Category | null;
  source: "history" | "model" | "none";
  confidence: "low" | "medium" | "high" | null;
}

export interface CategoryForecast {
  category_id: string;
  name: string;
  color: string;
  spent: Money;
  projected: Money;
  budget: Money | null;
  projected_status: BudgetStatus | null;
  will_exceed_budget: boolean;
}

export interface GoalForecast {
  goal_id: string;
  name: string;
  remaining: Money;
  monthly_pace: Money;
  projected_completion: string | null;
  target_date: string | null;
  on_track: boolean | null;
}

export interface Forecast {
  month: string;
  currency: string;
  available: boolean;
  reason: string | null;
  is_estimate: boolean;
  elapsed_days: number;
  days_in_month: number;
  spent_so_far: Money;
  projected_expense: Money;
  categories: CategoryForecast[];
  budget_warnings: CategoryForecast[];
  goals: GoalForecast[];
}

export interface InsightFact {
  id: string;
  label: string;
  value: string;
}

export interface Insight {
  title: string;
  body: string;
  tone: "positive" | "neutral" | "warning";
  facts: InsightFact[];
}

export interface InsightsResponse {
  month: string;
  available: boolean;
  reason: string | null;
  insights: Insight[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  data_used: { tool: string; description: string }[];
}

export interface ReceiptScan {
  readable: boolean;
  merchant: string | null;
  transaction_date: string | null;
  amount: Money | null;
  currency: string | null;
  category: Category | null;
  message: string | null;
  transaction_type: TransactionType;
}
