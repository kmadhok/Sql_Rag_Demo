// Pure helpers that turn a BigQuery result into what the canvas shows:
// column roles, chart kind, headline numbers, a one-line summary, and formatting.

const ID_PATTERN = /(^id$|_id$|^id_)/i;
const TIME_NAME_PATTERN = /(date|time|month|week|day|year|quarter|_at$)/i;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}(-\d{2})?([ T]\d{2}:\d{2})?/;
const MONEY_PATTERN = /(value|revenue|sales|price|amount|spend|spent|cost|profit|aov|gmv)/i;
const AVERAGE_PATTERN = /(avg|average|mean|rate|ratio|pct|percent|share)/i;
const MAX_BAR_ROWS = 15;

export function humanize(column) {
  const words = String(column).replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function isNumeric(value) {
  if (typeof value === "number") return Number.isFinite(value);
  return typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value));
}

function nonNullValues(rows, column) {
  return rows.map((row) => row[column]).filter((v) => v !== null && v !== undefined && v !== "");
}

function isTimeColumn(rows, column) {
  const values = nonNullValues(rows, column);
  if (values.length === 0) return false;
  if (values.every((v) => typeof v === "string" && ISO_DATE_PATTERN.test(v))) return true;
  return TIME_NAME_PATTERN.test(column) && !values.every(isNumeric);
}

// Year-like integer columns (e.g. "year": 2024) are time, not measures.
function isYearColumn(rows, column) {
  const values = nonNullValues(rows, column);
  return /year/i.test(column) && values.length > 0 && values.every((v) => isNumeric(v) && Number(v) >= 1900 && Number(v) <= 2100);
}

// Integer period parts such as month 1-12 or quarter 1-4 (only within their valid range).
const PERIOD_PARTS = [[/month/i, 1, 12], [/quarter/i, 1, 4], [/week/i, 1, 53], [/day/i, 1, 31]];

function isPeriodPart(rows, column) {
  const range = PERIOD_PARTS.find(([pattern]) => pattern.test(column));
  const values = nonNullValues(rows, column);
  return Boolean(range) && values.length > 0 && values.every((v) => isNumeric(v) && Number.isInteger(Number(v)) && Number(v) >= range[1] && Number(v) <= range[2]);
}

// Time axis columns: a date column, or year and/or a period part (e.g. order_year + order_month).
function timeColumns(rows, columns) {
  const date = columns.find((c) => isTimeColumn(rows, c));
  if (date) return [date];
  const parts = [columns.find((c) => isYearColumn(rows, c)), columns.find((c) => isPeriodPart(rows, c))].filter(Boolean);
  return parts.length ? parts : null;
}

export function detectRoles(rows) {
  if (!rows || rows.length === 0) return { columns: [], label: null, measure: null, time: null };
  const columns = Object.keys(rows[0]);

  const time = timeColumns(rows, columns);
  const isTime = (c) => Boolean(time && time.includes(c));
  const numeric = columns.filter((c) => !isTime(c) && nonNullValues(rows, c).length > 0 && nonNullValues(rows, c).every(isNumeric));
  const measure = numeric.find((c) => !ID_PATTERN.test(c)) || null;

  let label = null;
  if (columns.includes("first_name") && columns.includes("last_name")) {
    label = { columns: ["first_name", "last_name"], name: "Name" };
  } else {
    const text = columns.find((c) => !isTime(c) && !numeric.includes(c));
    const fallbackId = numeric.find((c) => ID_PATTERN.test(c));
    const pick = text || fallbackId;
    if (pick) label = { columns: [pick], name: humanize(pick) };
  }

  return { columns, label, measure, time };
}

export function labelOf(row, label) {
  if (!label) return "";
  return label.columns.map((c) => row[c]).filter((v) => v !== null && v !== undefined).join(" ");
}

export function formatNumber(value, column = "") {
  if (!isNumeric(value)) return value === null || value === undefined ? "–" : String(value);
  const n = Number(value);
  const money = MONEY_PATTERN.test(column);
  const abs = Math.abs(n);
  let text;
  if (abs >= 1e9) text = `${(n / 1e9).toFixed(2)}B`;
  else if (abs >= 1e6) text = `${(n / 1e6).toFixed(2)}M`;
  else if (money && abs >= 100) text = Math.round(n).toLocaleString("en-US");
  else if (Number.isInteger(n)) text = n.toLocaleString("en-US");
  else text = n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return money ? `$${text}` : text;
}

export function formatBytes(bytes) {
  if (!isNumeric(bytes)) return "–";
  const n = Number(bytes);
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)} MB`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} KB`;
  return `${n} B`;
}

export function formatSeconds(seconds) {
  if (!isNumeric(seconds)) return "–";
  const n = Number(seconds);
  return n < 10 ? `${n.toFixed(1)}s` : `${Math.round(n)}s`;
}

function timeText(row, time) {
  if (time.length === 2) return `${row[time[0]]}-${String(row[time[1]]).padStart(2, "0")}`;
  const s = String(row[time[0]]);
  return ISO_DATE_PATTERN.test(s) ? s.slice(0, s.length >= 10 ? 10 : 7) : s;
}

const chartNote = (count) => (count > MAX_BAR_ROWS ? `top ${MAX_BAR_ROWS} charted` : "all charted");

// Decide what the canvas renders for a result set.
export function analyzeResult(rows) {
  const roles = detectRoles(rows);
  const { label, measure, time } = roles;
  const count = rows ? rows.length : 0;

  if (count === 0) {
    return { roles, chart: { kind: "none" }, kpis: [], summary: "The query returned no rows." };
  }

  if (count === 1 && measure) {
    const value = formatNumber(rows[0][measure], measure);
    return {
      roles,
      chart: { kind: "none" },
      kpis: [{ title: humanize(measure), value, detail: label ? labelOf(rows[0], label) : "" }],
      summary: `${humanize(measure)}: ${value}${label ? ` (${labelOf(rows[0], label)})` : ""}.`,
    };
  }

  if (!measure) {
    return { roles, chart: { kind: "none" }, kpis: [], summary: `Found ${count.toLocaleString("en-US")} rows.` };
  }

  const numbers = rows.map((r) => Number(r[measure])).filter(Number.isFinite);
  const isAverage = AVERAGE_PATTERN.test(measure);
  const aggregate = isAverage
    ? { title: "Average", value: formatNumber(numbers.reduce((a, b) => a + b, 0) / numbers.length, measure), detail: `${humanize(measure).toLowerCase()}, ${count.toLocaleString("en-US")} rows` }
    : { title: "Total", value: formatNumber(numbers.reduce((a, b) => a + b, 0), measure), detail: `${humanize(measure).toLowerCase()}, ${count.toLocaleString("en-US")} rows` };

  if (time) {
    const points = rows
      .map((r) => ({ x: timeText(r, time), y: Number(r[measure]) }))
      .filter((p) => Number.isFinite(p.y))
      .sort((a, b) => (isNumeric(a.x) && isNumeric(b.x) ? Number(a.x) - Number(b.x) : a.x < b.x ? -1 : a.x > b.x ? 1 : 0));
    const peak = points.reduce((best, p) => (p.y > best.y ? p : best), points[0]);
    return {
      roles,
      chart: { kind: "line", points, measure },
      kpis: [
        { title: "Peak", value: formatNumber(peak.y, measure), detail: peak.x },
        aggregate,
        { title: "Periods", value: points.length.toLocaleString("en-US"), detail: `${points[0].x} → ${points[points.length - 1].x}` },
      ],
      summary: `Peak ${humanize(measure).toLowerCase()} was ${formatNumber(peak.y, measure)} in ${peak.x}.`,
    };
  }

  if (label) {
    const bars = rows.slice(0, MAX_BAR_ROWS).map((r) => ({ x: labelOf(r, label), y: Number(r[measure]) }));
    const top = bars[0];
    return {
      roles,
      chart: { kind: "bar", points: bars, measure, truncated: count > MAX_BAR_ROWS },
      kpis: [
        { title: "Top result", value: formatNumber(top.y, measure), detail: top.x },
        aggregate,
        { title: "Rows", value: count.toLocaleString("en-US"), detail: chartNote(count) },
      ],
      summary: `Found ${count.toLocaleString("en-US")} rows. ${top.x} leads at ${formatNumber(top.y, measure)}.`,
    };
  }

  return { roles, chart: { kind: "none" }, kpis: [aggregate], summary: `Found ${count.toLocaleString("en-US")} rows.` };
}

// Tables referenced in the SQL, in first-seen order.
export function tablesFromSql(sql) {
  const found = [];
  const pattern = /thelook_ecommerce\.(\w+)/g;
  let match;
  while ((match = pattern.exec(sql || "")) !== null) {
    if (!found.includes(match[1])) found.push(match[1]);
  }
  return found;
}

// Turn API/network failures into something a visitor can read.
export function readableError(error) {
  const raw = (error && (error.message || String(error))) || "";
  if (/failed to fetch|networkerror|load failed/i.test(raw)) {
    return "Can't reach the API right now. It may be starting up; try again in a few seconds.";
  }
  let detail = raw;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.detail === "string") detail = parsed.detail;
  } catch {
    // not JSON; keep raw text
  }
  if (/no result/i.test(detail)) return "The model couldn't produce a query for that question. Try rephrasing it.";
  if (/api key|401|unauthori[sz]ed/i.test(detail)) return "The AI service rejected our credentials. This is on our side, not yours.";
  if (/quota|rate limit|429/i.test(detail)) return "The AI service is busy. Try again in a minute.";
  return detail.length > 240 ? `${detail.slice(0, 240)}…` : detail || "Something went wrong.";
}
