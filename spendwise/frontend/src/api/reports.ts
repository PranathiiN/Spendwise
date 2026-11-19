import { apiClient } from "./client";
import type { MonthlyReport } from "../types";

export const reportsApi = {
  async monthly(month: string): Promise<MonthlyReport> {
    const { data } = await apiClient.get<MonthlyReport>("/reports/monthly", { params: { month } });
    return data;
  },
  /** Downloads the month's transactions as a CSV file (sent with the auth header). */
  async downloadCsv(month: string): Promise<void> {
    const response = await apiClient.get<Blob>("/reports/monthly/export", {
      params: { month },
      responseType: "blob",
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `spendwise-${month}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
