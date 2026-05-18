// Temporary identity: stores the user's UUID in localStorage.
// All API calls pick this up via apiFetch and send it as X-User-Id.
// Replace with a real auth token when the auth milestone lands.

const KEY = "micro_habit_user_id";

export function getUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function setUserId(id: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, id);
}

export function clearUserId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
}
