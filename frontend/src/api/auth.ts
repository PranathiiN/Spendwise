import { apiClient } from "./client";
import type { TokenResponse, User } from "../types";

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  preferred_currency?: string;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/register", payload);
    return data;
  },
  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", { email, password });
    return data;
  },
  async me(): Promise<User> {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },
  async updateProfile(payload: { name?: string; preferred_currency?: string }): Promise<User> {
    const { data } = await apiClient.patch<User>("/auth/me", payload);
    return data;
  },
  async changePassword(current_password: string, new_password: string): Promise<void> {
    await apiClient.post("/auth/change-password", { current_password, new_password });
  },
};
