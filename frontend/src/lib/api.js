const rawBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD
    ? "https://transfermarketscrap.onrender.com/app"
    : "http://127.0.0.1:8000/app");

export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");

export function apiUrl(path) {
  const cleanPath = path.replace(/^\//, "");
  return `${API_BASE_URL}/${cleanPath}`;
}

export async function fetchJson(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.error || payload?.detail || "Request failed.";
    throw new Error(message);
  }

  return payload;
}
