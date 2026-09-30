import { useEffect, useRef, useState } from "react";
import { formatSeconds } from "./analyzeResult.js";

function Spinner() {
  return <span className="inline-block size-3 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" aria-hidden="true" />;
}

function TurnStatus({ turn }) {
  if (turn.status === "generating") return <p className="flex items-center gap-2 text-zinc-400"><Spinner /> Writing SQL…</p>;
  if (turn.status === "executing") return <p className="flex items-center gap-2 text-zinc-400"><Spinner /> Running on BigQuery…</p>;
  if (turn.status === "error") return <p className="text-rose-300">Couldn't answer: {turn.error}</p>;
  return (
    <>
      <p className="text-zinc-200">{turn.summary}</p>
      <p className="mt-1.5 text-xs text-zinc-500">
        {turn.execution?.totalRows?.toLocaleString("en-US")} rows · {formatSeconds((turn.finishedAt - turn.startedAt) / 1000)} total
      </p>
    </>
  );
}

function Composer({ onAsk, busy }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [text]);

  const submit = (event) => {
    event.preventDefault();
    if (!text.trim() || busy) return;
    onAsk(text);
    setText("");
  };

  return (
    <form onSubmit={submit} className="border-t border-line p-3">
      <label htmlFor="ask-input" className="sr-only">Ask a question</label>
      <div className="flex items-end gap-2 rounded-lg border border-line bg-panel p-2 focus-within:border-emerald-400/60">
        <textarea
          id="ask-input"
          ref={ref}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
          placeholder="Ask about orders, users, products…"
          className="max-h-40 flex-1 resize-none bg-transparent px-1 py-1 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="rounded-md bg-emerald-400 px-3 py-1.5 text-sm font-medium text-zinc-950 transition-opacity disabled:cursor-not-allowed disabled:opacity-30"
        >
          Ask
        </button>
      </div>
      <p className="mt-1.5 px-1 text-[11px] text-zinc-600">Enter to send · Shift+Enter for a new line</p>
    </form>
  );
}

export default function Thread({ turns, activeId, onSelect, onAsk, busy }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns.length]);

  return (
    <aside className="flex min-h-0 flex-col border-line md:border-r" aria-label="Conversation">
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 text-sm">
        {turns.length === 0 && (
          <p className="text-zinc-500">Your questions and answers show up here. Follow-ups keep the context, so you can ask "only in 2025" next.</p>
        )}
        {turns.map((turn) => {
          const active = turn.id === activeId;
          return (
            <div key={turn.id}>
              <p className="ml-auto w-fit max-w-[90%] rounded-lg bg-raised px-3 py-2 text-zinc-100">{turn.question}</p>
              <button
                type="button"
                onClick={() => onSelect(turn.id)}
                aria-pressed={active}
                className={`mt-2 block w-full rounded-lg border p-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-emerald-400 ${
                  active ? "border-emerald-400/50 bg-panel" : "border-line bg-transparent hover:bg-panel"
                }`}
              >
                <TurnStatus turn={turn} />
                {active && turn.status === "done" && <p className="mt-2 text-xs text-emerald-400">Showing in canvas →</p>}
              </button>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
      <Composer onAsk={onAsk} busy={busy} />
    </aside>
  );
}
