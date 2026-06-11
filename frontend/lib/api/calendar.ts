import { apiFetch } from "./client";
import type { CalendarStatusResponse } from "@/lib/types";

/** Get the current user's calendar connection status. */
export const getCalendarStatus = (): Promise<CalendarStatusResponse> =>
  apiFetch<CalendarStatusResponse>("/calendar/connection");

/**
 * Fetch the Google OAuth consent URL and redirect the browser to it.
 * Returns null if calendar integration is not configured on the server (503).
 */
export async function startCalendarConnect(): Promise<void> {
  const data = await apiFetch<{ url: string }>("/calendar/auth/url");
  window.location.href = data.url;
}

/** Disconnect the user's Google Calendar. */
export const disconnectCalendar = (): Promise<void> =>
  apiFetch<void>("/calendar/connection", { method: "DELETE" });
