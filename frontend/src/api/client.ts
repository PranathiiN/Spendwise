import axios, { AxiosError } from "axios";

export const TOKEN_KEY = "spendwise_token";
export const UNAUTHORIZED_EVENT = "spendwise:unauthorized";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
  timeout: 20000,
  headers: { "Content-Type": "application/json" },
});

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";
    const isAuthAttempt = url.includes("/auth/login") || url.includes("/auth/register");
    if (error.response?.status === 401 && !isAuthAttempt) {
      setToken(null);
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    return Promise.reject(error);
  },
);

interface FastApiValidationError {
  loc: (string | number)[];
  msg: string;
}

/** Turn any API/network error into a human-readable message. */
export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "Cannot reach the server. Is the backend running?";
    }
    const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return (detail as FastApiValidationError[])
        .map((d) => {
          const field = d.loc?.filter((p) => p !== "body").join(".");
          const msg = d.msg?.replace(/^Value error, /, "");
          return field ? `${field}: ${msg}` : msg;
        })
        .join("; ");
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
