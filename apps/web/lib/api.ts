export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

// The auth layer injects accessors so this module stays free of React imports.
let getToken: () => string | null = () => null;
let getAccountId: () => string = () => "";
let onUnauthorized: () => void = () => {};

export function setAuthAccessors(
  tokenFn: () => string | null,
  accountFn: () => string,
  unauthorizedFn: () => void
) {
  getToken = tokenFn;
  getAccountId = accountFn;
  onUnauthorized = unauthorizedFn;
}

function authHeaders(base: Record<string, string> = {}): Record<string, string> {
  const headers = { ...base };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const account = getAccountId();
  if (account) headers["X-Account-Id"] = account;
  return headers;
}

function handleStatus(status: number) {
  // A 401 means the token is missing/expired -> bounce to login.
  if (status === 401) onUnauthorized();
}

// Our API returns errors as {"detail": "..."}. Extract that for a clean
// message instead of surfacing the raw JSON body (or nothing at all) to the
// person using the app.
async function errorMessage(response: Response, path: string): Promise<string> {
  const text = await response.text().catch(() => "");
  if (text) {
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === "string") return parsed.detail;
    } catch {
      // Not JSON — fall through to using the raw text below.
    }
  }
  return text || `SpinningLicorice API ${response.status}: ${path}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!response.ok) {
    handleStatus(response.status);
    throw new Error(await errorMessage(response, path));
    throw new Error(`SpinningLicorice API ${response.status}: ${path}`);
  }
  return response.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    handleStatus(response.status);
    throw new Error(await errorMessage(response, path));
  }
  return response.json();
}

// For multipart file uploads (e.g. photo identification). FormData sets its
// own Content-Type with the correct multipart boundary, so we must NOT set
// one ourselves the way apiPost does for JSON bodies.
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    handleStatus(response.status);
    throw new Error(await errorMessage(response, path));
    const text = await response.text();
    throw new Error(text || `SpinningLicorice API ${response.status}: ${path}`);
  }
  return response.json();
}

export async function apiSend<T>(
  method: "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: unknown
): Promise<T | null> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: authHeaders(body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!response.ok) {
    handleStatus(response.status);
    throw new Error(await errorMessage(response, path));
    const text = await response.text();
    throw new Error(text || `SpinningLicorice API ${response.status}: ${path}`);
  }
  if (response.status === 204) return null;
  return response.json();
}
