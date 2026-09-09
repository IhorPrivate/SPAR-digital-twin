// Thin fetch wrapper around the backend REST API.
// Base URL is relative so the same bundle works behind the nginx proxy
// in docker-compose and behind the Vite dev proxy.

async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  cells: () => request("/cells"),
  cycles: (cellId) => request(`/cells/${cellId}/cycles`),
  predictions: (cellId) => request(`/cells/${cellId}/predictions`),
  train: (evaluate = true) => request("/train", { method: "POST", body: JSON.stringify({ evaluate }) }),
  metrics: () => request("/metrics"),
  twin: (cellId, horizon = 50) => request(`/twins/${cellId}?horizon=${horizon}`),
  ingest: (cellId, measurement) =>
    request(`/twins/${cellId}/ingest`, { method: "POST", body: JSON.stringify(measurement) }),
  resetTwin: (cellId) => request(`/twins/${cellId}`, { method: "DELETE" }),
};
