import { useMemo } from "react";
import { categoriesApi } from "../api/categories";
import type { Category } from "../types";
import { useApi } from "./useApi";

export function useCategories() {
  const { data, loading, error, reload } = useApi<Category[]>(() => categoriesApi.list(), []);
  const categories = useMemo(() => data ?? [], [data]);
  const expenseCategories = useMemo(() => categories.filter((c) => c.transaction_type === "expense"), [categories]);
  const incomeCategories = useMemo(() => categories.filter((c) => c.transaction_type === "income"), [categories]);
  return { categories, expenseCategories, incomeCategories, loading, error, reload };
}
