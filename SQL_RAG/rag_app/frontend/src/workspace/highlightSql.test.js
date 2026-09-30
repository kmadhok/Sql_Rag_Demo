import { describe, expect, it } from "vitest";
import { tokenizeSql } from "./highlightSql.js";

describe("tokenizeSql", () => {
  const sql = "-- top users\nSELECT u.id, SUM(oi.sale_price) AS total\nFROM `bigquery-public-data.thelook_ecommerce.users` u\nWHERE oi.status NOT IN ('Cancelled', 'Returned')\nLIMIT 10";

  it("round-trips the input exactly", () => {
    expect(tokenizeSql(sql).map((t) => t.text).join("")).toBe(sql);
  });

  it("classifies comments, keywords, tables, strings and numbers", () => {
    const byType = (type) => tokenizeSql(sql).filter((t) => t.type === type).map((t) => t.text);
    expect(byType("comment")).toEqual(["-- top users"]);
    expect(byType("keyword")).toEqual(expect.arrayContaining(["SELECT", "SUM", "AS", "FROM", "WHERE", "NOT", "IN", "LIMIT"]));
    expect(byType("table")).toEqual(["`bigquery-public-data.thelook_ecommerce.users`"]);
    expect(byType("string")).toEqual(["'Cancelled'", "'Returned'"]);
    expect(byType("number")).toEqual(["10"]);
  });

  it("does not treat keywords inside identifiers as keywords", () => {
    expect(tokenizeSql("select from_date").filter((t) => t.type === "keyword").map((t) => t.text)).toEqual(["select"]);
  });

  it("handles empty input", () => {
    expect(tokenizeSql("")).toEqual([]);
    expect(tokenizeSql(null)).toEqual([]);
  });
});
