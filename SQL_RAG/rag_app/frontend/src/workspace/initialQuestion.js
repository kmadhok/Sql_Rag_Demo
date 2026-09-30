export const MAX_QUESTION_LENGTH = 500;

// A question passed in the URL (e.g. /sql-rag?q=Monthly%20revenue), from links on kanumadhok.com.
export function initialQuestion(search) {
  const q = new URLSearchParams(search || "").get("q");
  const trimmed = (q || "").trim();
  return trimmed ? trimmed.slice(0, MAX_QUESTION_LENGTH) : null;
}
