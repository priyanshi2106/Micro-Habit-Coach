"use client";

/**
 * useNotifications — polls GET /notifications/pending and fires a browser
 * notification when the backend says it's time.
 *
 * Design constraints:
 * - No service worker, no VAPID keys — browser Notification API only.
 * - One notification per day maximum (enforced by the backend via
 *   last_acknowledged_at; the frontend acknowledges immediately after showing).
 * - Polls every POLL_INTERVAL_MS and on tab-focus (visibilitychange).
 * - Silently skips when Notification.permission !== "granted" or the
 *   Notification API is unavailable (e.g. in SSR / unsupported browsers).
 */

import { useEffect, useCallback } from "react";
import { getPendingNotification, acknowledgeNotification } from "@/lib/api/notifications";

const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function useNotifications(enabled: boolean): void {
  const checkAndNotify = useCallback(async () => {
    if (!notificationsSupported()) return;
    if (Notification.permission !== "granted") return;
    if (!enabled) return;

    try {
      const pending = await getPendingNotification();
      if (!pending.should_notify) return;

      const title = `Time for ${pending.habit_name ?? "your habit"}`;
      const body = pending.suggestion_reason
        ? `${pending.window_start}–${pending.window_end} · ${pending.suggestion_reason}`
        : `Window: ${pending.window_start}–${pending.window_end}`;

      new Notification(title, {
        body,
        icon: "/favicon.ico",
        tag: "habit-suggestion",  // prevents duplicate browser notifications
      });

      // Acknowledge immediately so the backend won't re-notify on the next poll.
      await acknowledgeNotification();
    } catch {
      // Silent — notification polling must never break the app.
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    // Poll immediately on mount, then on interval.
    checkAndNotify();
    const interval = setInterval(checkAndNotify, POLL_INTERVAL_MS);

    // Also poll when the tab regains focus.
    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        checkAndNotify();
      }
    }
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [enabled, checkAndNotify]);
}
