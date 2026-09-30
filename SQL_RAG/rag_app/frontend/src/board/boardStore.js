// Pinned answers live in the visitor's own browser: nothing is shared or stored server-side.

export const STORAGE_KEY = "sqlrag.pins.v1";
export const MAX_PIN_ROWS = 200;

export function loadPins(storage) {
  try {
    const parsed = JSON.parse(storage?.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.filter((p) => p && p.id && p.question && Array.isArray(p.rows)) : [];
  } catch {
    return [];
  }
}

// Returns false when the browser refuses to store (private mode, quota); the board still works in memory.
export function savePins(storage, pins) {
  try {
    storage?.setItem(STORAGE_KEY, JSON.stringify(pins));
    return Boolean(storage);
  } catch {
    return false;
  }
}

export function pinFromTurn(turn, now = new Date()) {
  return {
    id: `pin-${turn.id}`,
    question: turn.question,
    sql: turn.sql,
    rows: (turn.rows || []).slice(0, MAX_PIN_ROWS),
    execution: turn.execution,
    pinnedAt: now.toISOString(),
  };
}

export function addPin(pins, pin) {
  return [pin, ...pins.filter((p) => p.id !== pin.id)];
}

export function removePin(pins, id) {
  return pins.filter((p) => p.id !== id);
}

export function refreshPin(pins, id, exec, now = new Date()) {
  return pins.map((p) =>
    p.id === id
      ? {
          ...p,
          rows: (exec.data || []).slice(0, MAX_PIN_ROWS),
          execution: { totalRows: exec.total_rows ?? (exec.data || []).length, seconds: exec.execution_time, bytes: exec.bytes_processed, cacheHit: exec.cache_hit },
          refreshedAt: now.toISOString(),
        }
      : p
  );
}
