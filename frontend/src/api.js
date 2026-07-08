export const BACKEND_URL = (window.__BACKEND_URL__ || "http://localhost:8000").replace(/\/$/, "");

function authHeaders() {
  const token = localStorage.getItem("sl_token");
  return token ? { "x-token": token } : {};
}

async function parseJsonResponse(res) {
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const detail = (data && (data.detail || data.error)) || res.statusText || "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export async function apiGet(path, params) {
  const url = new URL(BACKEND_URL + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url, { headers: authHeaders() });
  return parseJsonResponse(res);
}

export async function apiPost(path, body) {
  const res = await fetch(BACKEND_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body || {}),
  });
  return parseJsonResponse(res);
}

export async function apiPut(path, body) {
  const res = await fetch(BACKEND_URL + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body || {}),
  });
  return parseJsonResponse(res);
}

export async function apiDelete(path) {
  const res = await fetch(BACKEND_URL + path, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return parseJsonResponse(res);
}

/**
 * Consumes a text/event-stream endpoint of the shape used by /ask-stream and
 * /ask-phd-stream: newline-delimited `data: {...}` blocks, each either
 * `{ text }` (a token to append) or `{ done: true, candidates }` (terminal).
 */
export async function streamQuery(path, query, { onToken, onDone, onError }) {
  try {
    const res = await fetch(BACKEND_URL + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...authHeaders() },
      body: JSON.stringify({ query }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`Server responded with ${res.status}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (!chunk.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(chunk.slice(6));
          if (data.text) onToken(data.text);
          if (data.done) {
            onDone(data.candidates || []);
            return;
          }
        } catch {
          /* ignore malformed chunk */
        }
      }
    }
    onDone([]);
  } catch (err) {
    onError(err);
  }
}
