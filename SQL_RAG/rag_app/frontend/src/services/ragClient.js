const rawBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";
const API_BASE = rawBase.replace(/\/+$/, "");


async function handleResponse(response) {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
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
  const response = await fetch(`${API_BASE}/sql/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
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

export const configInfo = {
  apiBase: API_BASE,
};
