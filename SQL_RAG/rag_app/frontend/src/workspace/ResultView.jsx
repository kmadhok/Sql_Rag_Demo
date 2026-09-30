import { Bar, BarChart, CartesianGrid, Cell, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatBytes, formatNumber, formatSeconds, humanize } from "./analyzeResult.js";

const ACCENT = "#34d399";
const ACCENT_MUTED = "#1f5f4a";
const AXIS = { fill: "#a1a1aa", fontSize: 12 };
const TOOLTIP = {
  contentStyle: { background: "#131316", border: "1px solid #26262b", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#e4e4e7" },
  itemStyle: { color: ACCENT },
  cursor: { fill: "rgb(255 255 255 / 0.04)" },
};
const MAX_TABLE_ROWS = 100;
const ID_COLUMN = /(^id$|_id$|^id_)/i;

function Kpi({ title, value, detail, large }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-3.5">
      <p className="text-xs text-zinc-500">{title}</p>
      <p className={`mt-1 font-semibold tracking-tight text-white tabular-nums ${large ? "text-4xl" : "text-2xl"}`}>{value}</p>
      {detail && <p className="mt-0.5 truncate text-xs text-zinc-500" title={detail}>{detail}</p>}
    </div>
  );
}

function ResultChart({ chart }) {
  const format = (v) => formatNumber(v, chart.measure);
  if (chart.kind === "bar") {
    const shortLabel = (s) => (String(s).length > 22 ? `${String(s).slice(0, 21)}…` : s);
    return (
      <figure className="rounded-xl border border-line bg-panel p-4">
        <figcaption className="mb-2 text-xs text-zinc-500">
          {humanize(chart.measure)}{chart.truncated ? ` · top ${chart.points.length} shown` : ""}
        </figcaption>
        <ResponsiveContainer width="100%" height={chart.points.length * 30 + 12}>
          <BarChart data={chart.points} layout="vertical" margin={{ top: 0, right: 64, bottom: 0, left: 0 }}>
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis type="category" dataKey="x" width={150} tick={AXIS} tickFormatter={shortLabel} axisLine={false} tickLine={false} />
            <Tooltip {...TOOLTIP} formatter={(v) => [format(v), humanize(chart.measure)]} />
            <Bar dataKey="y" barSize={18} radius={[0, 3, 3, 0]} isAnimationActive={false}>
              {chart.points.map((p, i) => <Cell key={`${p.x}-${i}`} fill={i === 0 ? ACCENT : ACCENT_MUTED} />)}
              <LabelList dataKey="y" position="right" formatter={format} fill="#d4d4d8" fontSize={12} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </figure>
    );
  }
  return (
    <figure className="rounded-xl border border-line bg-panel p-4">
      <figcaption className="mb-2 text-xs text-zinc-500">{humanize(chart.measure)} over time</figcaption>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chart.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#26262b" vertical={false} />
          <XAxis dataKey="x" tick={AXIS} axisLine={false} tickLine={false} minTickGap={28} />
          <YAxis tick={AXIS} tickFormatter={format} axisLine={false} tickLine={false} width={72} />
          <Tooltip {...TOOLTIP} formatter={(v) => [format(v), humanize(chart.measure)]} />
          <Line type="monotone" dataKey="y" stroke={ACCENT} strokeWidth={2} dot={chart.points.length <= 24} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}

function cellText(value, column) {
  if (value === null || value === undefined) return "–";
  if (typeof value === "number" && !ID_COLUMN.test(column)) return formatNumber(value, column);
  return String(value);
}

function ResultTable({ rows, totalRows }) {
  if (rows.length === 0) return null;
  const columns = Object.keys(rows[0]);
  const numeric = new Set(columns.filter((c) => rows.every((r) => r[c] === null || typeof r[c] === "number")));
  const shown = rows.slice(0, MAX_TABLE_ROWS);
  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-line bg-panel">
      <div className="max-h-[420px] overflow-auto">
        <table className="w-full text-[13px]">
          <thead className="sticky top-0 bg-panel text-left text-xs text-zinc-500">
            <tr className="border-b border-line">
              {columns.map((c) => (
                <th key={c} scope="col" className={`whitespace-nowrap px-3 py-2 font-medium ${numeric.has(c) ? "text-right" : ""}`}>{humanize(c)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, i) => (
              <tr key={i} className="border-b border-line/60 last:border-0">
                {columns.map((c) => (
                  <td
                    key={c}
                    className={`whitespace-nowrap px-3 py-2 ${numeric.has(c) ? "text-right tabular-nums" : ""} ${ID_COLUMN.test(c) ? "font-mono text-[12px] text-zinc-500" : "text-zinc-200"}`}
                  >
                    {cellText(row[c], c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalRows > shown.length && (
        <p className="border-t border-line px-3 py-2 text-xs text-zinc-500">Showing {shown.length} of {totalRows.toLocaleString("en-US")} rows</p>
      )}
    </div>
  );
}

export default function ResultView({ turn }) {
  const { analysis, rows, execution } = turn;
  const bigQuery = { title: "BigQuery", value: formatSeconds(execution.seconds), detail: `${formatBytes(execution.bytes)} scanned${execution.cacheHit ? " · cached" : ""}` };
  const kpis = [...analysis.kpis, bigQuery];
  const single = analysis.kpis.length === 1 && analysis.chart.kind === "none";
  const hasChart = analysis.chart.kind !== "none";

  return (
    <div className="space-y-3">
      <div className={`grid gap-3 ${single ? "sm:grid-cols-[2fr_1fr]" : "grid-cols-2 lg:grid-cols-4"}`}>
        {kpis.map((k, i) => <Kpi key={k.title} {...k} large={single && i === 0} />)}
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl border border-line bg-panel p-6 text-sm text-zinc-400">The query ran but returned no rows. Try widening the question, for example a longer date range.</p>
      ) : (
        <div className={`grid gap-3 ${hasChart ? "xl:grid-cols-[1.15fr_1fr]" : ""}`}>
          {hasChart && <ResultChart chart={analysis.chart} />}
          <ResultTable rows={rows} totalRows={execution.totalRows} />
        </div>
      )}
    </div>
  );
}
