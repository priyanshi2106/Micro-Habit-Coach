import { apiFetch } from "./client";
import type {
  NotificationPreference,
  NotificationPreferenceUpdate,
  NotificationPendingResponse,
} from "@/lib/types";

export const getNotificationPreferences = (): Promise<NotificationPreference> =>
  apiFetch<NotificationPreference>("/notifications/preferences");

export const updateNotificationPreferences = (
  body: NotificationPreferenceUpdate
): Promise<NotificationPreference> =>
  apiFetch<NotificationPreference>("/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify(body),
  });

export const getPendingNotification = (): Promise<NotificationPendingResponse> =>
  apiFetch<NotificationPendingResponse>("/notifications/pending");

export const acknowledgeNotification = (): Promise<void> =>
  apiFetch<void>("/notifications/acknowledge", { method: "POST" });
