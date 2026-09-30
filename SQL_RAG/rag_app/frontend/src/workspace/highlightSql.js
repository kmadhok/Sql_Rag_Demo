// Minimal SQL tokenizer for display. Returns [{ type, text }]; joining the texts
// reproduces the input exactly, so nothing is lost or reordered.

const TOKEN = new RegExp(
  [
    "(--[^\\n]*)", // comment
    "('(?:[^'\\\\]|\\\\.)*')", // string
    "(`[^`]*`)", // quoted identifier (table path)
    "\\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|FULL|OUTER|CROSS|ON|AND|OR|NOT|IN|IS|NULL|AS|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|WITH|UNION|ALL|DISTINCT|CASE|WHEN|THEN|ELSE|END|DESC|ASC|OVER|PARTITION|BETWEEN|LIKE|EXTRACT|INTERVAL|DATE_TRUNC|COUNT|SUM|AVG|MIN|MAX|ROUND|RANK|DENSE_RANK|ROW_NUMBER|COALESCE|CAST|DATE|TIMESTAMP)\\b", // keyword
    "\\b(\\d+(?:\\.\\d+)?)\\b", // number
  ].join("|"),
  "gi"
);

const TYPES = ["comment", "string", "table", "keyword", "number"];

export function tokenizeSql(sql) {
  const text = sql || "";
  const tokens = [];
  let last = 0;
  let match;
  TOKEN.lastIndex = 0;
  while ((match = TOKEN.exec(text)) !== null) {
    if (match.index > last) tokens.push({ type: "plain", text: text.slice(last, match.index) });
    const group = match.slice(1).findIndex((g) => g !== undefined);
    tokens.push({ type: TYPES[group], text: match[0] });
    last = match.index + match[0].length;
  }
  if (last < text.length) tokens.push({ type: "plain", text: text.slice(last) });
  return tokens;
}
