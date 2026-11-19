import { apiClient } from "./client";
import type { DashboardData } from "../types";

export const dashboardApi = {
  async get(month: string): Promise<DashboardData> {
    const { data } = await apiClient.get<DashboardData>("/dashboard", { params: { month } });
    return data;
  },
};
