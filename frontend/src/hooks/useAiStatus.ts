import { useEffect, useState } from "react";
import { aiApi } from "../api/ai";
import type { AIStatus } from "../types";

// Shared by every component and refreshed at most every 30 seconds, so starting
// Ollama (or downloading a model) is picked up without reloading the page.
const MAX_AGE_MS = 30_000;
// If the status check fails, keep SpendWise's own features visible (they report their own errors)
// and hide receipt scanning, which needs an outside model.
const OFF: AIStatus = {
  enabled: true,
  receipt_scanning: false,
  provider: "off",
  model: null,
  message: "Couldn't check whether receipt scanning is available.",
};
let cached: { at: number; promise: Promise<AIStatus> } | null = null;

function loadStatus(): Promise<AIStatus> {
  if (!cached || Date.now() - cached.at > MAX_AGE_MS) {
    cached = { at: Date.now(), promise: aiApi.status().catch(() => OFF) };
  }
  return cached.promise;
}

/** Which smart features are available. null while loading. */
export function useAiStatus(): AIStatus | null {
  const [status, setStatus] = useState<AIStatus | null>(null);
  useEffect(() => {
    let cancelled = false;
    loadStatus().then((s) => {
      if (!cancelled) setStatus(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return status;
}
