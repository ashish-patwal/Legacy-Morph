const localHosts = new Set(["localhost", "127.0.0.1"]);

function resolveApiUrl() {
  const configuredUrl = import.meta.env.VITE_BACKEND_URL;

  if (typeof window === "undefined") {
    return configuredUrl || "http://localhost:8000";
  }

  if (!configuredUrl) {
    return localHosts.has(window.location.hostname)
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : window.location.origin;
  }

  try {
    const apiUrl = new URL(configuredUrl);
    if (
      localHosts.has(apiUrl.hostname) &&
      localHosts.has(window.location.hostname)
    ) {
      apiUrl.hostname = window.location.hostname;
      return apiUrl.origin;
    }
  } catch {
    return configuredUrl;
  }

  return configuredUrl;
}

const API_URL = resolveApiUrl();

function apiUrl(path) {
  return `${API_URL}${path}`;
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new Error(detail);
  }

  return response.json();
}

async function downloadFile(path) {
  const response = await fetch(apiUrl(path));

  if (!response.ok) {
    let detail = `Download failed with status ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // Keep the status-based message when the body is not JSON.
    }
    throw new Error(detail);
  }

  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.[1] || "legacy-morph-package.zip",
  };
}

export const api = {
  health: () => request("/health"),
  inspectRepository: (payload) =>
    request("/repositories/inspect", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createSession: (payload) =>
    request("/migration-sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  latestPackage: () => request("/migration-sessions/latest-package"),
  analyze: (migrationSessionId) =>
    request("/analyze", {
      method: "POST",
      body: JSON.stringify({ migration_session_id: migrationSessionId }),
    }),
  createPlan: (sessionId) =>
    request(`/migration-sessions/${sessionId}/plan`, { method: "POST" }),
  approvePlan: (sessionId) =>
    request(`/migration-sessions/${sessionId}/plan/approve`, { method: "POST" }),
  migrate: (migrationSessionId) =>
    request("/migrate", {
      method: "POST",
      body: JSON.stringify({ migration_session_id: migrationSessionId }),
    }),
  reviewFile: (fileId, payload) =>
    request(`/generated-files/${fileId}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  packageUrl: (migrationSessionId) =>
    apiUrl(`/migration-sessions/${migrationSessionId}/package`),
  downloadPackage: (migrationSessionId) =>
    downloadFile(`/migration-sessions/${migrationSessionId}/package`),
};
