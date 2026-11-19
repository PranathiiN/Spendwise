import { apiClient } from "./client";
import type {
  AIStatus,
  CategorySuggestion,
  ChatMessage,
  ChatResponse,
  Forecast,
  InsightsResponse,
  PaymentMethod,
  ReceiptScan,
  TransactionType,
} from "../types";

// AI calls can take longer than ordinary API calls.
const AI_TIMEOUT = 90000;

export const aiApi = {
  async status(): Promise<AIStatus> {
    const { data } = await apiClient.get<AIStatus>("/ai/status");
    return data;
  },

  async suggestCategory(input: {
    description: string;
    transaction_type: TransactionType;
    amount?: string | null;
    payment_method?: PaymentMethod | null;
  }): Promise<CategorySuggestion> {
    const { data } = await apiClient.post<CategorySuggestion>("/ai/categorize", input, { timeout: 30000 });
    return data;
  },

  async insights(month: string): Promise<InsightsResponse> {
    const { data } = await apiClient.get<InsightsResponse>("/ai/insights", { params: { month }, timeout: AI_TIMEOUT });
    return data;
  },

  async chat(messages: ChatMessage[]): Promise<ChatResponse> {
    const { data } = await apiClient.post<ChatResponse>("/ai/chat", { messages }, { timeout: AI_TIMEOUT });
    return data;
  },

  async scanReceipt(file: File): Promise<ReceiptScan> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await apiClient.post<ReceiptScan>("/ai/receipt", form, {
      timeout: AI_TIMEOUT,
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};

export const forecastApi = {
  async get(month: string): Promise<Forecast> {
    const { data } = await apiClient.get<Forecast>("/forecast", { params: { month } });
    return data;
  },
};
