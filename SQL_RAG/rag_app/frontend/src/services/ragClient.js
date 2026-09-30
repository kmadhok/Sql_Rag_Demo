// In development a localhost fallback is fine; production builds must set VITE_API_BASE_URL.
const rawBase = import.meta.env.DEV
  ? import.meta.env.VITE_API_BASE_URL || "http://localhost:8080"
  : import.meta.env.VITE_API_BASE_URL;

if (!rawBase) {
  throw new Error("VITE_API_BASE_URL is not configured. Production builds require --build-arg VITE_API_BASE_URL=<url>");
}

const API_BASE = rawBase.endsWith("/") ? rawBase.slice(0, -1) : rawBase;

async function post(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error((await response.text()) || response.statusText);
  }
  return response.json();
}

// Generate SQL for a question (retrieval + LLM).
export function runQuerySearch(payload) {
  return post("/query/search", payload);
}

// Run SQL on BigQuery. A 200 response can still carry success: false.
export function executeSql(payload) {
  return post("/sql/execute", payload);
}
