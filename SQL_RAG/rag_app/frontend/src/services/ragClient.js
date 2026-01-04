import chartDebugger from '../utils/chartDebugger.js';

// === PRODUCTION HARDENING: Environment-aware API URL configuration ===
// In development mode: Allow localhost fallback for convenience
// In production mode: Require explicit VITE_API_BASE_URL, fail fast if missing
const rawBase = import.meta.env.DEV
  ? (import.meta.env.VITE_API_BASE_URL || "http://localhost:8080")  // Dev: fallback OK
  : import.meta.env.VITE_API_BASE_URL;                               // Prod: no fallback

// Production safety check - fail fast if URL missing
if (!rawBase) {
  throw new Error(
    "FATAL: VITE_API_BASE_URL is not configured! " +
    "Production builds require --build-arg VITE_API_BASE_URL=<url>"
  );
}

const API_BASE = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase;


async function handleResponse(response, context = {}) {
  const { method = 'GET', url = '', startTime = null } = context;

  if (!response.ok) {
    const text = await response.text();

    // Log error details
    chartDebugger.error('API', `${method} ${url} failed`, {
      status: response.status,
      statusText: response.statusText,
      body: text,
      duration: startTime ? Date.now() - startTime : null,
    });

    console.error('⚠️ API Error Response:', {
      status: response.status,
      statusText: response.statusText,
      body: text
    });

    throw new Error(text || response.statusText);
  }

  const data = await response.json();
  const duration = startTime ? Date.now() - startTime : null;

  // Log successful response
  chartDebugger.apiResponse(method, url, response.status, {
    dataKeys: data ? Object.keys(data) : [],
    duration: duration ? `${duration}ms` : null,
  });

  console.log('✨ Parsed JSON response:', data);
  return data;
}

export async function runQuerySearch(payload) {
  const response = await fetch(`${API_BASE}/query/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function executeSql(payload) {
  try {
    const url = `${API_BASE}/sql/execute`;
    console.log('🌐 Fetch URL:', url);
    console.log('📦 Payload:', payload);

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    console.log('📥 Response status:', response.status, response.statusText);
    return handleResponse(response);
  } catch (error) {
    console.error('🔥 Network error in executeSql:', error);
    throw new Error(`Network error: ${error.message}`);
  }
}

export async function runQuickAnswer(payload) {
  const response = await fetch(`${API_BASE}/query/quick`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function saveQuery(payload) {
  const response = await fetch(`${API_BASE}/saved_queries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function listSavedQueries() {
  const response = await fetch(`${API_BASE}/saved_queries`);
  return handleResponse(response);
}

export async function getSavedQuery(id) {
  const url = `${API_BASE}/saved_queries/${id}`;
  const method = 'GET';
  const startTime = Date.now();

  // Log request
  chartDebugger.apiRequest(method, url, id);

  try {
    const response = await fetch(url);
    return handleResponse(response, { method, url, startTime });
  } catch (error) {
    // Log network errors
    chartDebugger.error('API', `${method} ${url} network error`, {
      savedQueryId: id,
      error: error.message,
      duration: `${Date.now() - startTime}ms`,
    });
    throw error;
  }
}

// Dashboard API methods
export async function createDashboard(payload) {
  const response = await fetch(`${API_BASE}/dashboards`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function listDashboards() {
  const response = await fetch(`${API_BASE}/dashboards`);
  return handleResponse(response);
}

export async function getDashboard(id) {
  const url = `${API_BASE}/dashboards/${id}`;
  const method = 'GET';
  const startTime = Date.now();

  chartDebugger.apiRequest(method, url, id);

  try {
    const response = await fetch(url);
    return handleResponse(response, { method, url, startTime });
  } catch (error) {
    chartDebugger.error('API', `${method} ${url} network error`, {
      dashboardId: id,
      error: error.message,
      duration: `${Date.now() - startTime}ms`,
    });
    throw error;
  }
}

export async function updateDashboard(id, payload) {
  const response = await fetch(`${API_BASE}/dashboards/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function duplicateDashboard(id) {
  const response = await fetch(`${API_BASE}/dashboards/${id}/duplicate`, {
    method: "POST",
  });
  return handleResponse(response);
}

export async function deleteDashboard(id) {
  const response = await fetch(`${API_BASE}/dashboards/${id}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

export async function getTables() {
  const response = await fetch(`${API_BASE}/schema/tables`);
  return handleResponse(response);
}

export async function getTableColumns(tableName) {
  const response = await fetch(`${API_BASE}/schema/tables/${encodeURIComponent(tableName)}/columns`);
  return handleResponse(response);
}

export async function getTableDescription(tableName) {
  const response = await fetch(`${API_BASE}/schema/tables/${encodeURIComponent(tableName)}/description`);
  return handleResponse(response);
}

// Week 4: AI-Powered SQL Assistance API methods
export async function explainSql(payload) {
  const response = await fetch(`${API_BASE}/sql/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function completeSql(payload) {
  const response = await fetch(`${API_BASE}/sql/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function fixSql(payload) {
  const response = await fetch(`${API_BASE}/sql/fix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function formatSql(payload) {
  const response = await fetch(`${API_BASE}/sql/format`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function chatSql(payload) {
  const response = await fetch(`${API_BASE}/sql/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export const configInfo = {
  apiBase: API_BASE,
};
