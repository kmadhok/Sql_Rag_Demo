import { useCallback, useEffect, useRef, useState } from "react";
import { executeSql, runQuerySearch, saveQuery } from "../services/ragClient.js";
import { askFlow, DEFAULT_SETTINGS, historyText } from "./askFlow.js";

const api = { runQuerySearch, executeSql };

export function useAsk({ onSaved } = {}) {
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

  const save = useCallback(
    async (id) => {
      const turn = turnsRef.current.find((t) => t.id === id);
      if (!turn || turn.status !== "done" || turn.saving) return;
      patchTurn(id, { saving: true, saveError: null });
      try {
        const saved = await saveQuery({ question: turn.question, sql: turn.sql, data: turn.rows });
        patchTurn(id, { saving: false, savedId: saved.id });
        onSaved?.(saved);
      } catch (err) {
        patchTurn(id, { saving: false, saveError: "Couldn't save. Try again." });
      }
    },
    [patchTurn, onSaved]
  );

  const activeTurn = turns.find((t) => t.id === activeId) || null;
  return { turns, activeTurn, setActiveId, ask, save, busy, settings, setSettings };
}
