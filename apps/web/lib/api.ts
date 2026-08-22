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

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!response.ok) {
    handleStatus(response.status);
    throw new Error(`Burnt Jacket API ${response.status}: ${path}`);
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
    const text = await response.text();
    throw new Error(text || `Burnt Jacket API ${response.status}: ${path}`);
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
    const text = await response.text();
    throw new Error(text || `Burnt Jacket API ${response.status}: ${path}`);
  }
  if (response.status === 204) return null;
  return response.json();
}
