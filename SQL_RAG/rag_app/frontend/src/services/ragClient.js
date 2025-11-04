const rawBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";
const API_BASE = rawBase.replace(/\/+$/, "");


async function handleResponse(response) {
  if (!response.ok) {
    const text = await response.text();
    console.error('⚠️ API Error Response:', {
      status: response.status,
      statusText: response.statusText,
      body: text
    });
    throw new Error(text || response.statusText);
  }

  const data = await response.json();
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
  const response = await fetch(`${API_BASE}/saved_queries/${id}`);
  return handleResponse(response);
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
  const response = await fetch(`${API_BASE}/dashboards/${id}`);
  return handleResponse(response);
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
