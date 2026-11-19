import { apiClient } from "./client";
import type { SavingsGoal, SavingsGoalPayload } from "../types";

export const goalsApi = {
  async list(): Promise<SavingsGoal[]> {
    const { data } = await apiClient.get<SavingsGoal[]>("/goals");
    return data;
  },
  async create(payload: SavingsGoalPayload): Promise<SavingsGoal> {
    const { data } = await apiClient.post<SavingsGoal>("/goals", payload);
    return data;
  },
  async update(id: string, payload: Partial<Omit<SavingsGoalPayload, "current_amount">>): Promise<SavingsGoal> {
    const { data } = await apiClient.patch<SavingsGoal>(`/goals/${id}`, payload);
    return data;
  },
  async contribute(id: string, amount: string, action: "deposit" | "withdraw"): Promise<SavingsGoal> {
    const { data } = await apiClient.post<SavingsGoal>(`/goals/${id}/contribute`, { amount, action });
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/goals/${id}`);
  },
};
