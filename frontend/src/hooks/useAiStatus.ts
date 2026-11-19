import { useEffect, useState } from "react";
import { aiApi } from "../api/ai";
import type { AIStatus } from "../types";

// Fetched once per page load and shared by every component.
let cached: Promise<AIStatus> | null = null;

/** Whether AI features are switched on (ANTHROPIC_API_KEY set on the server). null while loading. */
export function useAiStatus(): AIStatus | null {
  const [status, setStatus] = useState<AIStatus | null>(null);
  useEffect(() => {
    let cancelled = false;
    cached ??= aiApi.status().catch(() => {
      cached = null; // retry on the next mount
      return { enabled: false, model: null };
    });
    cached.then((s) => {
      if (!cancelled) setStatus(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return status;
}
