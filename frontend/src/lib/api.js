const API_BASE = "/api";


async function fetchJson(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    let detailMessage = `Request failed for ${path}: HTTP ${response.status}`;

    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        detailMessage = errorBody.detail;
      }
    } catch (error) {
      // Keep the default HTTP error message when the body is not JSON.
    }

    throw new Error(detailMessage);
  }

  return response.json();
}


export async function fetchBackendSnapshot() {
  const results = await Promise.allSettled([
    fetchJson("/health"),
    fetchJson("/source"),
    fetchJson("/status"),
    fetchJson("/detections"),
    fetchJson("/cameras"),
  ]);

  const snapshot = {
    health: null,
    source: null,
    status: null,
    detections: null,
    cameras: null,
    errors: [],
  };

  const keys = ["health", "source", "status", "detections", "cameras"];

  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    const key = keys[index];

    if (result.status === "fulfilled") {
      snapshot[key] = result.value;
      continue;
    }

    snapshot.errors.push(`${key}: ${result.reason.message}`);
  }

  return snapshot;
}


export async function switchBackendSource(payload) {
  return fetchJson("/source/select", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}


export function buildSnapshotImageUrl() {
  const cacheBreaker = Date.now();
  return `${API_BASE}/snapshot?ts=${cacheBreaker}`;
}
