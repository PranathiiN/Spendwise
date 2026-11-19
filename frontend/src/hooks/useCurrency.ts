import { useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { formatCurrency } from "../utils/currency";

/** Returns a formatter bound to the user's preferred currency. */
export function useCurrency() {
  const { user } = useAuth();
  const currency = user?.preferred_currency ?? "INR";
  const format = useCallback(
    (value: string | number | null | undefined, compact = false) => formatCurrency(value, currency, { compact }),
    [currency],
  );
  return { currency, format };
}
