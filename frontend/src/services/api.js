const API_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
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
  generateTests: (migrationSessionId, generatedFileIds) =>
    request("/generate-tests", {
      method: "POST",
      body: JSON.stringify({
        migration_session_id: migrationSessionId,
        generated_file_ids: generatedFileIds,
      }),
    }),
  validate: (migrationSessionId, generatedFileIds, testCases) =>
    request("/validate", {
      method: "POST",
      body: JSON.stringify({
        migration_session_id: migrationSessionId,
        generated_file_ids: generatedFileIds,
        test_cases: testCases,
      }),
    }),
};
