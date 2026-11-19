import { apiClient } from "./client";
import type { Transaction, TransactionFilters, TransactionListResponse, TransactionPayload } from "../types";

/** Drop empty filter values so they are not sent as `?search=`. */
function cleanParams(filters: TransactionFilters): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params[key] = value as string | number;
    }
  }
  return params;
}

export const transactionsApi = {
  async list(filters: TransactionFilters): Promise<TransactionListResponse> {
    const { data } = await apiClient.get<TransactionListResponse>("/transactions", {
      params: cleanParams(filters),
    });
    return data;
  },
  async get(id: string): Promise<Transaction> {
    const { data } = await apiClient.get<Transaction>(`/transactions/${id}`);
    return data;
  },
  async create(payload: TransactionPayload): Promise<Transaction> {
    const { data } = await apiClient.post<Transaction>("/transactions", payload);
    return data;
  },
  async update(id: string, payload: Partial<TransactionPayload>): Promise<Transaction> {
    const { data } = await apiClient.patch<Transaction>(`/transactions/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/transactions/${id}`);
  },
};
