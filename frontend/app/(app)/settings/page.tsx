"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { getCalendarStatus, startCalendarConnect, disconnectCalendar } from "@/lib/api/calendar";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
} from "@/lib/api/notifications";
import type { CalendarStatusResponse, NotificationPreference } from "@/lib/types";

const NOTIFY_MINUTE_OPTIONS = [5, 10, 15, 30];
const CONFIDENCE_OPTIONS: Array<{ value: number; label: string }> = [
  { value: 0.45, label: "Any" },
  { value: 0.65, label: "Medium" },
  { value: 0.80, label: "High" },
];

export default function SettingsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // ── Calendar state ──────────────────────────────────────────────────────────
  const [status, setStatus] = useState<CalendarStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [calendarUnavailable, setCalendarUnavailable] = useState(false);

  // ── Notifications state ─────────────────────────────────────────────────────
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreference | null>(null);
  const [notifLoading, setNotifLoading] = useState(true);
  const [notifSaving, setNotifSaving] = useState(false);
  const [notifError, setNotifError] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);

  // Banner shown after returning from Google OAuth.
  const justConnected = searchParams.get("connected") === "true";
  const oauthError = searchParams.get("error");

  useEffect(() => {
    // Clear OAuth query params from the URL so they don't persist on refresh.
    if (justConnected || oauthError) {
      router.replace("/settings", { scroll: false });
    }
  }, [justConnected, oauthError, router]);

  useEffect(() => {
    getCalendarStatus()
      .then(setStatus)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load calendar status");
      })
      .finally(() => setLoading(false));

    getNotificationPreferences()
      .then(setNotifPrefs)
      .catch(() => { /* non-fatal */ })
      .finally(() => setNotifLoading(false));
  }, []);

  async function handleConnect() {
    setConnecting(true);
    setError(null);
    try {
      await startCalendarConnect();
      // startCalendarConnect redirects; this line only runs on failure.
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start connection";
      if (msg.includes("503") || msg.includes("not configured")) {
        setCalendarUnavailable(true);
      } else {
        setError(msg);
      }
      setConnecting(false);
    }
  }

  async function handleNotifChange(patch: Partial<NotificationPreference>) {
    if (!notifPrefs) return;
    const next = { ...notifPrefs, ...patch };
    setNotifError(null);
    setPermissionDenied(false);

    // When enabling, request browser permission first.
    if (patch.enabled === true && typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "denied") {
        setPermissionDenied(true);
        return;
      }
      if (Notification.permission === "default") {
        const result = await Notification.requestPermission();
        if (result !== "granted") {
          setPermissionDenied(true);
          return;
        }
      }
    }

    setNotifSaving(true);
    try {
      const saved = await updateNotificationPreferences({
        enabled: next.enabled,
        notify_minutes_before: next.notify_minutes_before,
        confidence_threshold: next.confidence_threshold,
      });
      setNotifPrefs(saved);
    } catch (err: unknown) {
      setNotifError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setNotifSaving(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    setError(null);
    try {
      await disconnectCalendar();
      setStatus({ connected: false, connection: null });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Account
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
      </div>

      {/* OAuth result banners */}
      {justConnected && (
        <div className="mb-5 rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Google Calendar connected. Your suggestions will now respect your real availability.
        </div>
      )}
      {oauthError && (
        <div className="mb-5 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not connect Google Calendar ({oauthError}). Please try again.
        </div>
      )}
      {error && (
        <div className="mb-5 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Notifications section */}
      <section className="mb-6">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Notifications
        </h2>

        <div className="rounded-xl border border-rim bg-white p-5">
          <p className="text-sm font-semibold text-ink">Habit reminders</p>
          <p className="mt-0.5 text-xs text-ink-muted">
            Get a browser notification when it&apos;s time for your suggested habit.
          </p>

          {notifError && (
            <p className="mt-2 text-xs text-red-600">{notifError}</p>
          )}
          {permissionDenied && (
            <p className="mt-2 text-xs text-amber-600">
              Browser notifications are blocked. Allow them in your browser settings, then try again.
            </p>
          )}

          <div className="mt-4">
            {notifLoading ? (
              <div className="h-8 w-40 animate-pulse rounded-lg bg-rim" />
            ) : notifPrefs ? (
              <div className="space-y-4">
                {/* Enable toggle */}
                <label className="flex items-center gap-3 cursor-pointer">
                  <button
                    role="switch"
                    aria-checked={notifPrefs.enabled}
                    disabled={notifSaving}
                    onClick={() => handleNotifChange({ enabled: !notifPrefs.enabled })}
                    className={[
                      "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent",
                      "transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2",
                      "focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-40",
                      notifPrefs.enabled ? "bg-accent" : "bg-rim",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm",
                        "transition-transform duration-200",
                        notifPrefs.enabled ? "translate-x-4" : "translate-x-0",
                      ].join(" ")}
                    />
                  </button>
                  <span className="text-sm text-ink">
                    {notifPrefs.enabled ? "Enabled" : "Disabled"}
                  </span>
                  {notifSaving && (
                    <span className="text-xs text-ink-subtle">Saving…</span>
                  )}
                </label>

                {/* Fine-grained controls — only shown when enabled */}
                {notifPrefs.enabled && (
                  <div className="space-y-3 pl-0">
                    {/* Notify minutes before */}
                    <div className="flex items-center gap-3">
                      <label className="w-24 text-xs text-ink-muted">Notify</label>
                      <select
                        value={notifPrefs.notify_minutes_before}
                        disabled={notifSaving}
                        onChange={(e) =>
                          handleNotifChange({
                            notify_minutes_before: parseInt(e.target.value, 10),
                          })
                        }
                        className="rounded border border-rim bg-white px-2 py-1 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-40"
                      >
                        {NOTIFY_MINUTE_OPTIONS.map((m) => (
                          <option key={m} value={m}>
                            {m} min before
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Confidence level */}
                    <div className="flex items-center gap-3">
                      <label className="w-24 text-xs text-ink-muted">Minimum</label>
                      <select
                        value={notifPrefs.confidence_threshold}
                        disabled={notifSaving}
                        onChange={(e) =>
                          handleNotifChange({
                            confidence_threshold: parseFloat(e.target.value),
                          })
                        }
                        className="rounded border border-rim bg-white px-2 py-1 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-40"
                      >
                        {CONFIDENCE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                      <span className="text-xs text-ink-subtle">confidence</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-ink-subtle">Could not load notification preferences.</p>
            )}
          </div>
        </div>
      </section>

      {/* Integrations section */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Integrations
        </h2>

        <div className="rounded-xl border border-rim bg-white p-5">
          {/* Card header */}
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-ink">Google Calendar</p>
              <p className="mt-0.5 text-xs text-ink-muted">
                Read-only. Your busy times are subtracted from suggestion windows.
              </p>
            </div>

            {/* Status badge */}
            {!loading && status && (
              <span
                className={[
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  status.connected
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-surface text-ink-subtle",
                ].join(" ")}
              >
                {status.connected ? "Connected" : "Not connected"}
              </span>
            )}
          </div>

          {/* Body */}
          <div className="mt-4">
            {loading ? (
              <div className="h-8 w-40 animate-pulse rounded-lg bg-rim" />
            ) : calendarUnavailable ? (
              <p className="text-xs text-ink-subtle">
                Google Calendar integration is not enabled on this server.
              </p>
            ) : status?.connected && status.connection ? (
              <div className="space-y-3">
                <p className="text-xs text-ink-muted">
                  Connected as{" "}
                  <span className="font-medium text-ink">
                    {status.connection.google_account_email}
                  </span>
                </p>
                <button
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                  className="text-xs text-ink-subtle hover:text-red-600 transition-colors disabled:opacity-40"
                >
                  {disconnecting ? "Disconnecting…" : "Disconnect"}
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <button
                  onClick={handleConnect}
                  disabled={connecting}
                  className={[
                    "inline-flex items-center gap-1.5 rounded-lg border border-rim bg-white px-3 py-1.5",
                    "text-xs font-medium text-ink shadow-sm hover:bg-surface transition-colors",
                    "disabled:opacity-40",
                  ].join(" ")}
                >
                  {connecting ? "Opening Google…" : "Connect Google Calendar"}
                </button>
                <p className="text-xs text-ink-subtle">
                  No events are read — only whether a time slot is free or busy.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
