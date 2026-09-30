import { describe, expect, it } from "vitest";
import { addPin, loadPins, MAX_PIN_ROWS, pinFromTurn, refreshPin, removePin, savePins, STORAGE_KEY } from "./boardStore.js";
import exampleBoard from "./exampleBoard.json";
import { analyzeResult } from "../workspace/analyzeResult.js";

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; }, data };
}

const TURN = {
  id: "t1",
  question: "Top brands",
  sql: "SELECT 1",
  rows: Array.from({ length: 250 }, (_, i) => ({ brand: `B${i}`, revenue: i })),
  execution: { totalRows: 250, seconds: 1.2, bytes: 100 },
};
const NOW = new Date("2026-09-30T12:00:00Z");

describe("loading pins", () => {
  it("returns an empty list when nothing is stored", () => {
    expect(loadPins(memoryStorage())).toEqual([]);
  });

  it("returns an empty list when storage is unavailable or throws", () => {
    expect(loadPins(undefined)).toEqual([]);
    expect(loadPins({ getItem: () => { throw new Error("SecurityError"); } })).toEqual([]);
  });

  it("ignores corrupt JSON, non-arrays and malformed entries", () => {
    expect(loadPins(memoryStorage({ [STORAGE_KEY]: "{not json" }))).toEqual([]);
    expect(loadPins(memoryStorage({ [STORAGE_KEY]: '{"a":1}' }))).toEqual([]);
    const mixed = JSON.stringify([{ id: "ok", question: "q", rows: [] }, { id: "no-rows", question: "q" }, null]);
    expect(loadPins(memoryStorage({ [STORAGE_KEY]: mixed })).map((p) => p.id)).toEqual(["ok"]);
  });

  it("round-trips what was saved", () => {
    const storage = memoryStorage();
    const pins = [pinFromTurn(TURN, NOW)];
    expect(savePins(storage, pins)).toBe(true);
    expect(loadPins(storage)).toEqual(pins);
  });
});

describe("saving pins", () => {
  it("reports failure instead of throwing when the browser refuses (quota, private mode)", () => {
    expect(savePins({ setItem: () => { throw new Error("QuotaExceededError"); } }, [])).toBe(false);
    expect(savePins(undefined, [])).toBe(false);
  });
});

describe("pinning", () => {
  it("captures question, SQL, run details and at most MAX_PIN_ROWS rows", () => {
    const pin = pinFromTurn(TURN, NOW);
    expect(pin).toMatchObject({ id: "pin-t1", question: "Top brands", sql: "SELECT 1", execution: TURN.execution, pinnedAt: "2026-09-30T12:00:00.000Z" });
    expect(pin.rows).toHaveLength(MAX_PIN_ROWS);
  });

  it("puts the newest pin first and does not duplicate a re-pinned answer", () => {
    const a = pinFromTurn({ ...TURN, id: "a" }, NOW);
    const b = pinFromTurn({ ...TURN, id: "b" }, NOW);
    expect(addPin(addPin([], a), b).map((p) => p.id)).toEqual(["pin-b", "pin-a"]);
    expect(addPin([b, a], a).map((p) => p.id)).toEqual(["pin-a", "pin-b"]);
  });

  it("removes a pin by id and ignores unknown ids", () => {
    const pins = [pinFromTurn({ ...TURN, id: "a" }), pinFromTurn({ ...TURN, id: "b" })];
    expect(removePin(pins, "pin-a").map((p) => p.id)).toEqual(["pin-b"]);
    expect(removePin(pins, "missing")).toHaveLength(2);
  });
});

describe("refreshing", () => {
  it("replaces rows and run details for one pin only", () => {
    const pins = [pinFromTurn({ ...TURN, id: "a" }), pinFromTurn({ ...TURN, id: "b" })];
    const next = refreshPin(pins, "pin-a", { data: [{ brand: "X", revenue: 9 }], total_rows: 1, execution_time: 0.8, bytes_processed: 5, cache_hit: true }, NOW);
    expect(next[0]).toMatchObject({ rows: [{ brand: "X", revenue: 9 }], execution: { totalRows: 1, seconds: 0.8, bytes: 5, cacheHit: true }, refreshedAt: "2026-09-30T12:00:00.000Z" });
    expect(next[1]).toBe(pins[1]);
  });
});

describe("example board", () => {
  it("has four well-formed cards that each produce a chart", () => {
    expect(exampleBoard).toHaveLength(4);
    for (const card of exampleBoard) {
      expect(card).toMatchObject({ id: expect.any(String), question: expect.any(String), sql: expect.stringMatching(/SELECT/i) });
      expect(card.rows.length).toBeGreaterThan(0);
      expect(analyzeResult(card.rows).chart.kind).not.toBe("none");
    }
  });
});
