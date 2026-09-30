import { describe, expect, it } from "vitest";
import {
  analyzeResult,
  detectRoles,
  formatBytes,
  formatNumber,
  formatSeconds,
  humanize,
  readableError,
  tablesFromSql,
} from "./analyzeResult.js";

const TOP_USERS = [
  { user_id: 99651, first_name: "Jonathan", last_name: "Kennedy", total_order_value: 2052.33 },
  { user_id: 94936, first_name: "Jonathon", last_name: "Barnes", total_order_value: 1924.63 },
  { user_id: 59525, first_name: "Robert", last_name: "Martinez", total_order_value: 1556.3 },
];

describe("column roles", () => {
  it("picks the first numeric non-ID column as the measure", () => {
    expect(detectRoles(TOP_USERS).measure).toBe("total_order_value");
  });

  it("combines first_name and last_name into one label", () => {
    expect(detectRoles(TOP_USERS).label.columns).toEqual(["first_name", "last_name"]);
  });

  it("uses the first text column as the label otherwise", () => {
    const rows = [{ category: "Jeans", returns: 120 }, { category: "Tops", returns: 90 }];
    expect(detectRoles(rows)).toMatchObject({ label: { columns: ["category"] }, measure: "returns", time: null });
  });

  it("falls back to an ID column as the label when there is no text column", () => {
    const rows = [{ user_id: 1, spend: 10 }, { user_id: 2, spend: 5 }];
    expect(detectRoles(rows)).toMatchObject({ label: { columns: ["user_id"] }, measure: "spend" });
  });

  it("treats numeric strings as numbers", () => {
    const rows = [{ country: "US", aov: "85.20" }, { country: "UK", aov: "80.10" }];
    expect(detectRoles(rows).measure).toBe("aov");
  });

  it("detects ISO date values as time even without a date-like name", () => {
    const rows = [{ period: "2025-01-01", revenue: 1 }, { period: "2025-02-01", revenue: 2 }];
    expect(detectRoles(rows).time).toEqual(["period"]);
  });

  it("detects year integer columns as time, not as the measure", () => {
    const rows = [{ year: 2024, orders: 10 }, { year: 2025, orders: 20 }];
    expect(detectRoles(rows)).toMatchObject({ time: ["year"], measure: "orders" });
  });

  it("combines separate year and month integer columns into one time axis", () => {
    const rows = [
      { order_year: 2025, order_month: 2, revenue: 200 },
      { order_year: 2025, order_month: 1, revenue: 100 },
    ];
    const roles = detectRoles(rows);
    expect(roles).toMatchObject({ time: ["order_year", "order_month"], measure: "revenue" });
    const result = analyzeResult(rows);
    expect(result.chart.kind).toBe("line");
    expect(result.chart.points.map((p) => p.x)).toEqual(["2025-01", "2025-02"]);
    expect(result.summary).toBe("Peak revenue was $200 in 2025-02.");
  });

  it("treats a month-number column without a year as time, not as the measure", () => {
    const rows = Array.from({ length: 12 }, (_, i) => ({ month: i + 1, signups: 100 + i }));
    expect(detectRoles(rows)).toMatchObject({ time: ["month"], measure: "signups" });
  });

  it("sorts numeric periods numerically, not as text", () => {
    const rows = [10, 2, 1].map((m) => ({ month: m, signups: m * 10 }));
    expect(analyzeResult(rows).chart.points.map((p) => p.x)).toEqual(["1", "2", "10"]);
  });

  it("does not treat an out-of-range 'day' count as a period", () => {
    const rows = [{ category: "A", days_to_ship: 45 }, { category: "B", days_to_ship: 60 }];
    expect(detectRoles(rows)).toMatchObject({ time: null, measure: "days_to_ship" });
  });

  it("returns empty roles for no rows", () => {
    expect(detectRoles([])).toEqual({ columns: [], label: null, measure: null, time: null });
  });
});

describe("analyzeResult", () => {
  it("renders a bar chart with Top / Total / Rows for label + measure", () => {
    const result = analyzeResult(TOP_USERS);
    expect(result.chart.kind).toBe("bar");
    expect(result.chart.points[0]).toEqual({ x: "Jonathan Kennedy", y: 2052.33 });
    expect(result.kpis.map((k) => k.title)).toEqual(["Top result", "Total", "Rows"]);
    expect(result.kpis[0]).toMatchObject({ value: "$2,052", detail: "Jonathan Kennedy" });
    expect(result.kpis[1].value).toBe("$5,533");
    expect(result.summary).toBe("Found 3 rows. Jonathan Kennedy leads at $2,052.");
  });

  it("caps bar charts at 15 bars and marks them truncated", () => {
    const rows = Array.from({ length: 20 }, (_, i) => ({ brand: `B${i}`, revenue: 100 - i }));
    const { chart } = analyzeResult(rows);
    expect(chart.points).toHaveLength(15);
    expect(chart.truncated).toBe(true);
  });

  it("renders a line chart sorted by time with the peak", () => {
    const rows = [
      { month: "2025-03", revenue: 300 },
      { month: "2025-01", revenue: 100 },
      { month: "2025-02", revenue: 500 },
    ];
    const result = analyzeResult(rows);
    expect(result.chart.kind).toBe("line");
    expect(result.chart.points.map((p) => p.x)).toEqual(["2025-01", "2025-02", "2025-03"]);
    expect(result.kpis[0]).toMatchObject({ title: "Peak", value: "$500", detail: "2025-02" });
    expect(result.summary).toBe("Peak revenue was $500 in 2025-02.");
  });

  it("shows an average instead of a total for rate-like measures", () => {
    const rows = [{ country: "US", avg_order_value: 90 }, { country: "UK", avg_order_value: 70 }];
    expect(analyzeResult(rows).kpis[1]).toMatchObject({ title: "Average", value: "$80", detail: "avg order value, 2 rows" });
  });

  it("shows a single KPI for a one-row, one-value result", () => {
    const result = analyzeResult([{ total_revenue: 8046468 }]);
    expect(result.chart.kind).toBe("none");
    expect(result.kpis).toEqual([{ title: "Total revenue", value: "$8.05M", detail: "" }]);
    expect(result.summary).toBe("Total revenue: $8.05M.");
  });

  it("handles results with no numeric measure", () => {
    const result = analyzeResult([{ name: "a" }, { name: "b" }]);
    expect(result).toMatchObject({ chart: { kind: "none" }, kpis: [], summary: "Found 2 rows." });
  });

  it("handles an empty result", () => {
    expect(analyzeResult([])).toMatchObject({ chart: { kind: "none" }, summary: "The query returned no rows." });
    expect(analyzeResult(undefined).summary).toBe("The query returned no rows.");
  });
});

describe("formatting", () => {
  it("formats money-like columns with a dollar sign and no cents above $100", () => {
    expect(formatNumber(2052.33, "total_order_value")).toBe("$2,052");
    expect(formatNumber(85.2, "aov")).toBe("$85.2");
  });

  it("formats plain counts with thousands separators and compacts large values", () => {
    expect(formatNumber(124814, "orders")).toBe("124,814");
    expect(formatNumber(8046468, "orders")).toBe("8.05M");
    expect(formatNumber(2.5e9, "events")).toBe("2.50B");
  });

  it("returns a dash for missing values and passes text through", () => {
    expect(formatNumber(null)).toBe("–");
    expect(formatNumber("n/a")).toBe("n/a");
  });

  it("formats bytes and seconds", () => {
    expect(formatBytes(7195169)).toBe("7.2 MB");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(undefined)).toBe("–");
    expect(formatSeconds(1.7633)).toBe("1.8s");
    expect(formatSeconds(19.56)).toBe("20s");
  });

  it("humanizes column names", () => {
    expect(humanize("total_order_value")).toBe("Total order value");
  });
});

describe("tablesFromSql", () => {
  it("lists thelook tables once, in order of appearance", () => {
    const sql = "SELECT * FROM `bigquery-public-data.thelook_ecommerce.users` u JOIN `bigquery-public-data.thelook_ecommerce.order_items` oi ON 1=1 JOIN `bigquery-public-data.thelook_ecommerce.users` u2 ON 1=1";
    expect(tablesFromSql(sql)).toEqual(["users", "order_items"]);
  });

  it("returns an empty list for missing SQL", () => {
    expect(tablesFromSql(null)).toEqual([]);
  });
});

describe("readableError", () => {
  it("extracts FastAPI detail from a JSON body", () => {
    expect(readableError(new Error('{"detail":"Question is empty."}'))).toBe("Question is empty.");
  });

  it("explains network failures", () => {
    expect(readableError(new TypeError("Failed to fetch"))).toMatch(/Can't reach the API/);
  });

  it("maps known pipeline failures to plain language", () => {
    expect(readableError(new Error('{"detail":"RAG pipeline returned no result."}'))).toMatch(/couldn't produce a query/);
    expect(readableError(new Error("400 API key not valid"))).toMatch(/credentials/);
    expect(readableError(new Error("429 rate limit"))).toMatch(/busy/);
  });

  it("truncates very long messages and handles empty errors", () => {
    expect(readableError(new Error("x".repeat(500)))).toHaveLength(241);
    expect(readableError(null)).toBe("Something went wrong.");
  });
});
