/**
 * Auth API calls — login, register, refresh, logout.
 *
 * These do NOT use apiFetch because they run before the access token exists
 * (or are used to obtain it). They call fetch directly so they can set the
 * Authorization header only when explicitly given a token.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  timezone: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

async function authFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    // credentials: "include" is required so the browser sends and receives
    // the HTTP-only refresh cookie on /auth/* routes.
    credentials: "include",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const json = await res.json();
      if (typeof json?.detail === "string") detail = json.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const registerUser = (payload: RegisterPayload): Promise<TokenResponse> =>
  authFetch<TokenResponse>("/auth/register", payload);

export const loginUser = (payload: LoginPayload): Promise<TokenResponse> =>
  authFetch<TokenResponse>("/auth/login", payload);

/**
 * Silently restore the session using the HTTP-only refresh cookie.
 * Called on app load. Returns null if no valid cookie exists.
 */
export async function refreshSession(): Promise<TokenResponse | null> {
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json() as Promise<TokenResponse>;
  } catch {
    return null;
  }
}

export const logoutUser = (): Promise<void> =>
  authFetch<void>("/auth/logout", {});
