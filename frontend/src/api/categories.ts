import { apiClient } from "./client";
import type { Category, TransactionType } from "../types";

export interface CategoryPayload {
  name: string;
  transaction_type: TransactionType;
  color: string;
  icon_name?: string;
}

export const categoriesApi = {
  async list(transaction_type?: TransactionType): Promise<Category[]> {
    const { data } = await apiClient.get<Category[]>("/categories", {
      params: transaction_type ? { transaction_type } : undefined,
    });
    return data;
  },
  async create(payload: CategoryPayload): Promise<Category> {
    const { data } = await apiClient.post<Category>("/categories", payload);
    return data;
  },
  async update(id: string, payload: Partial<Omit<CategoryPayload, "transaction_type">>): Promise<Category> {
    const { data } = await apiClient.patch<Category>(`/categories/${id}`, payload);
    return data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`/categories/${id}`);
  },
};
