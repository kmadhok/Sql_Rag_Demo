import { tokenizeSql } from "./highlightSql.js";

const COLORS = {
  keyword: "text-emerald-300",
  string: "text-rose-300",
  number: "text-amber-300",
  table: "text-zinc-400",
  comment: "text-zinc-500 italic",
  plain: "text-zinc-200",
};

export default function SqlBlock({ sql, className = "" }) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-line bg-panel p-4 font-mono text-[12.5px] leading-relaxed ${className}`}>
      <code className="block whitespace-pre">
        {tokenizeSql(sql).map((t, i) => (
          <span key={i} className={COLORS[t.type]}>{t.text}</span>
        ))}
      </code>
    </div>
  );
}
