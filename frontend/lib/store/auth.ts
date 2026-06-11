/**
 * In-memory access token store.
 *
 * The access token is intentionally NOT stored in localStorage or
 * sessionStorage — keeping it in a module variable means XSS cannot
 * exfiltrate it. The trade-off is that a hard page refresh clears it;
 * the session bootstrap in the app layout silently restores it via the
 * HTTP-only refresh cookie (see app/(app)/layout.tsx).
 */

let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string): void {
  _accessToken = token;
}

export function clearAccessToken(): void {
  _accessToken = null;
}
