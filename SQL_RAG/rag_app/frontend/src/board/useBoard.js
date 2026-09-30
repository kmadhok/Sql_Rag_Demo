import { useCallback, useEffect, useState } from "react";
import { executeSql } from "../services/ragClient.js";
import { readableError } from "../workspace/analyzeResult.js";
import { MAX_BYTES_BILLED } from "../workspace/askFlow.js";
import { addPin, loadPins, pinFromTurn, refreshPin, removePin, savePins } from "./boardStore.js";
import exampleBoard from "./exampleBoard.json";

const storage = (() => {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
})();

export function useBoard() {
  const [pins, setPins] = useState(() => loadPins(storage));
  const [examples, setExamples] = useState(exampleBoard);
  const [refreshing, setRefreshing] = useState({});
  const [errors, setErrors] = useState({});
  const [persisted, setPersisted] = useState(true);

  useEffect(() => {
    setPersisted(savePins(storage, pins));
  }, [pins]);

  const pin = useCallback((turn) => setPins((prev) => addPin(prev, pinFromTurn(turn))), []);
  const unpin = useCallback((id) => setPins((prev) => removePin(prev, id)), []);
  const isPinned = useCallback((turnId) => pins.some((p) => p.id === `pin-${turnId}`), [pins]);

  // Re-run a card's SQL live. Example cards refresh in memory only.
  const refresh = useCallback(async (card) => {
    setRefreshing((r) => ({ ...r, [card.id]: true }));
    setErrors((e) => ({ ...e, [card.id]: null }));
    try {
      const exec = await executeSql({ sql: card.sql, dry_run: false, max_bytes_billed: MAX_BYTES_BILLED });
      if (!exec.success) throw new Error(exec.error_message || "BigQuery rejected the query.");
      const update = (list) => refreshPin(list, card.id, exec);
      if (card.id.startsWith("example-")) setExamples(update);
      else setPins(update);
    } catch (err) {
      setErrors((e) => ({ ...e, [card.id]: readableError(err) }));
    } finally {
      setRefreshing((r) => ({ ...r, [card.id]: false }));
    }
  }, []);

  return { pins, examples, pin, unpin, isPinned, refresh, refreshing, errors, persisted };
}
