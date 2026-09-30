import { describe, expect, it } from "vitest";
import { initialQuestion, MAX_QUESTION_LENGTH } from "./initialQuestion.js";

describe("initialQuestion", () => {
  it("reads and decodes the q parameter", () => {
    expect(initialQuestion("?q=Monthly%20revenue%20in%202025")).toBe("Monthly revenue in 2025");
    expect(initialQuestion("?q=Top+10+customers")).toBe("Top 10 customers");
  });

  it("ignores other parameters", () => {
    expect(initialQuestion("?utm_source=site&q=Orders+by+status")).toBe("Orders by status");
  });

  it("returns null when q is missing, empty or whitespace", () => {
    expect(initialQuestion("")).toBeNull();
    expect(initialQuestion(undefined)).toBeNull();
    expect(initialQuestion("?q=")).toBeNull();
    expect(initialQuestion("?q=%20%20")).toBeNull();
  });

  it("caps very long questions", () => {
    expect(initialQuestion(`?q=${"a".repeat(2000)}`)).toHaveLength(MAX_QUESTION_LENGTH);
  });
});
