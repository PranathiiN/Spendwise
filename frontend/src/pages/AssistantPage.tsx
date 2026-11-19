import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { aiApi } from "../api/ai";
import { getErrorMessage } from "../api/client";
import { EmptyState, ErrorAlert, PageHeader } from "../components/common/Feedback";
import { Icon } from "../components/common/Icon";
import { PageLoader, Spinner } from "../components/common/Spinner";
import { useAiStatus } from "../hooks/useAiStatus";
import type { ChatMessage, ChatResponse } from "../types";

interface Turn extends ChatMessage {
  dataUsed?: ChatResponse["data_used"];
}

const EXAMPLES = [
  "How much did I spend on food last month?",
  "Which category grew the most compared with last month?",
  "Am I on track with my budgets this month?",
  "How long until I reach my savings goals?",
];

/** SW-14: read-only chat assistant over the user's own data. */
export function AssistantPage() {
  const ai = useAiStatus();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, sending]);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || sending) return;
    const history: Turn[] = [...turns, { role: "user", content: question }];
    setTurns(history);
    setInput("");
    setError(null);
    setSending(true);
    try {
      const res = await aiApi.chat(history.map(({ role, content }) => ({ role, content })));
      setTurns([...history, { role: "assistant", content: res.reply, dataUsed: res.data_used }]);
    } catch (err) {
      setError(getErrorMessage(err, "The assistant couldn't answer. Try again."));
      setTurns(turns); // drop the unanswered question so it can be re-sent
      setInput(question);
    } finally {
      setSending(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };

  if (ai === null) return <PageLoader />;

  return (
    <div className="flex flex-col">
      <PageHeader
        title="Assistant"
        subtitle="Ask questions about your spending, budgets and goals. It can read your data but can't change anything."
        actions={
          turns.length > 0 && (
            <button type="button" className="btn-secondary" onClick={() => setTurns([])} disabled={sending}>
              New chat
            </button>
          )
        }
      />

      {!ai.enabled ? (
        <EmptyState
          title="The assistant is switched off"
          description="Add an ANTHROPIC_API_KEY to backend/.env and restart the backend to turn on AI features."
        />
      ) : (
        <div className="card flex min-h-[60vh] flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto pb-4" aria-live="polite">
            {turns.length === 0 && (
              <div className="py-6 text-center">
                <Icon name="chat" className="mx-auto h-8 w-8 text-brand-700" />
                <p className="mt-2 text-sm text-slate-600">Try asking:</p>
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((q) => (
                    <button key={q} type="button" className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50" onClick={() => void send(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((t, i) => (
              <div key={i} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    t.role === "user" ? "bg-brand-700 text-white" : "bg-slate-100 text-slate-900"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{t.content}</p>
                  {t.dataUsed && t.dataUsed.length > 0 && (
                    <details className="mt-2 text-xs text-slate-500">
                      <summary className="cursor-pointer select-none hover:text-slate-700">Data used</summary>
                      <ul className="mt-1 list-disc space-y-0.5 pl-4">
                        {t.dataUsed.map((d, j) => (
                          <li key={j}>{d.description}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex items-center gap-2 text-sm text-slate-500" role="status">
                <Spinner className="h-4 w-4" /> Looking at your data...
              </div>
            )}
            <div ref={endRef} />
          </div>

          <ErrorAlert message={error} />
          <form onSubmit={onSubmit} className="mt-3 flex items-end gap-2 border-t border-slate-100 pt-3">
            <label htmlFor="chat-input" className="sr-only">Your question</label>
            <textarea
              id="chat-input"
              rows={1}
              maxLength={4000}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about your finances..."
              className="input max-h-40 min-h-[42px] flex-1 resize-y"
              disabled={sending}
            />
            <button type="submit" className="btn-primary" disabled={sending || !input.trim()} aria-label="Send">
              <Icon name="send" className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
