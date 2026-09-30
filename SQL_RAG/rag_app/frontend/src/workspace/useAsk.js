import { useCallback, useEffect, useRef, useState } from "react";
import { executeSql, runQuerySearch } from "../services/ragClient.js";
import { askFlow, DEFAULT_SETTINGS, historyText } from "./askFlow.js";

const api = { runQuerySearch, executeSql };

export function useAsk() {
  const [turns, setTurns] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const turnsRef = useRef(turns);
  useEffect(() => {
    turnsRef.current = turns;
  }, [turns]);

  const patchTurn = useCallback((id, patch) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  }, []);

  const busy = turns.some((t) => t.status === "generating" || t.status === "executing");

  const ask = useCallback(
    async (question) => {
      const trimmed = question.trim();
      if (!trimmed || busy) return;
      const id = `${Date.now()}`;
      const history = historyText(turnsRef.current);
      setTurns((prev) => [...prev, { id, question: trimmed, status: "generating", startedAt: Date.now() }]);
      setActiveId(id);
      await askFlow({ question: trimmed, history, settings }, api, (patch) => patchTurn(id, patch));
    },
    [busy, settings, patchTurn]
  );

  const activeTurn = turns.find((t) => t.id === activeId) || null;
  return { turns, activeTurn, setActiveId, ask, busy, settings, setSettings };
}
