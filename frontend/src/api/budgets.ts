import { apiClient } from "./client";
import type { Budget, BudgetListResponse } from "../types";

export interface BudgetCreatePayload {
  category_id: string;
  month: string;
  amount: string;
  alert_threshold: number;
}

export const budgetsApi = {
  async list(month: string): Promise<BudgetListResponse> {
    const { data } = await apiClient.get<BudgetListResponse>("/budgets", { params: { month } });
    return data;
  },
  async create(payload: BudgetCreatePayload): Promise<Budget> {
    const { data } = await apiClient.post<Budget>("/budgets", payload);
    return data;
  },
  async update(id: string, payload: { amount?: string; alert_threshold?: number }): Promise<Budget> {
    const { data } = await apiClient.patch<Budget>(`/budgets/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/budgets/${id}`);
  },
  async copyPrevious(month: string): Promise<{ month: string; created: number }> {
    const { data } = await apiClient.post<{ month: string; created: number }>("/budgets/copy-previous", null, {
      params: { month },
    });
    return data;
  },
};
