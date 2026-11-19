import { useState, type FormEvent } from "react";
import { aiApi } from "../../api/ai";
import { getErrorMessage } from "../../api/client";
import { useAiStatus } from "../../hooks/useAiStatus";
import type { ParsedTransaction } from "../../types";
import { Icon } from "../common/Icon";
import { Spinner } from "../common/Spinner";

interface QuickAddBarProps {
  /** Called with the parsed fields; the parent opens the pre-filled form. */
  onParsed: (parsed: ParsedTransaction) => void;
}

/** SW-22: describe a transaction in plain words and get the form pre-filled. */
export function QuickAddBar({ onParsed }: QuickAddBarProps) {
  const ai = useAiStatus();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!ai?.enabled) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError(null);
    try {
      onParsed(await aiApi.parse(value));
      setText("");
    } catch (err) {
      setError(getErrorMessage(err, "Couldn't understand that. Try again or use Add transaction."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <label htmlFor="quick-add" className="sr-only">Describe a transaction</label>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Icon name="sparkles" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-brand-700" />
          <input
            id="quick-add"
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={500}
            disabled={busy}
            placeholder='Describe it, e.g. "paid 450 for lunch at Swiggy yesterday on UPI"'
            className="input pl-9"
          />
        </div>
        <button type="submit" className="btn-primary" disabled={busy || !text.trim()}>
          {busy ? <Spinner className="h-4 w-4" /> : null}
          {busy ? "Reading..." : "Fill in form"}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-[#a32727]" role="alert">{error}</p>}
    </form>
  );
}
