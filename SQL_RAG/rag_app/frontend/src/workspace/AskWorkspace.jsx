import { useState } from "react";
import Canvas from "./Canvas.jsx";
import Thread from "./Thread.jsx";
import Welcome from "./Welcome.jsx";

// Desktop: thread on the left, canvas on the right.
// Phones: one pane at a time, switching to the answer when a question is asked.
export default function AskWorkspace({ ask: state }) {
  const { turns, activeTurn, setActiveId, ask, save, busy, settings, setSettings } = state;
  const [pane, setPane] = useState("canvas");

  const askAndShow = (question) => {
    setPane("canvas");
    ask(question);
  };
  const select = (id) => {
    setActiveId(id);
    setPane("canvas");
  };

  const paneButton = (id, label) => (
    <button
      type="button"
      onClick={() => setPane(id)}
      aria-pressed={pane === id}
      className={`flex-1 rounded-md py-1.5 text-sm ${pane === id ? "bg-raised text-white" : "text-zinc-400"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="ws flex min-h-0 flex-1 flex-col md:grid md:grid-cols-[340px_1fr]">
      <div className="flex gap-1 border-b border-line p-2 md:hidden">
        {paneButton("thread", `Chat${turns.length ? ` (${turns.length})` : ""}`)}
        {paneButton("canvas", "Answer")}
      </div>

      <div className={`${pane === "thread" ? "flex" : "hidden"} min-h-0 flex-1 flex-col md:flex`}>
        <Thread turns={turns} activeId={activeTurn?.id} onSelect={select} onAsk={askAndShow} busy={busy} />
      </div>

      <main className={`${pane === "canvas" ? "block" : "hidden"} min-h-0 flex-1 overflow-y-auto md:block`}>
        {activeTurn ? (
          <Canvas turn={activeTurn} onSave={save} onRetry={askAndShow} settings={settings} onSettingsChange={setSettings} />
        ) : (
          <Welcome onAsk={askAndShow} busy={busy} />
        )}
        <div className="sticky bottom-0 p-3 md:hidden">
          <button type="button" onClick={() => setPane("thread")} className="w-full rounded-lg bg-emerald-400 py-2.5 text-sm font-medium text-zinc-950 shadow-lg">
            {turns.length ? "Ask a follow-up" : "Ask your own question"}
          </button>
        </div>
      </main>
    </div>
  );
}
