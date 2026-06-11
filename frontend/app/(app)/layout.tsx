"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { refreshSession, logoutUser } from "@/lib/api/auth";
import { getNotificationPreferences } from "@/lib/api/notifications";
import { setAccessToken, clearAccessToken, getAccessToken } from "@/lib/store/auth";
import { useNotifications } from "@/hooks/useNotifications";

// Pages that don't require a valid session (auth pages themselves).
const PUBLIC_PATHS = ["/login", "/onboarding"];

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  // Whether the user has enabled notifications — fetched once after session bootstrap.
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);

  // Mount the polling hook. It is a no-op when notificationsEnabled is false.
  useNotifications(notificationsEnabled);

  useEffect(() => {
    // If we already have a token in memory (navigated within the SPA), skip refresh.
    if (getAccessToken()) {
      setReady(true);
      return;
    }

    // Skip refresh check on public auth pages — let them render immediately.
    if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
      setReady(true);
      return;
    }

    // Silent refresh: browser sends the HTTP-only cookie automatically.
    refreshSession().then((result) => {
      if (result) {
        setAccessToken(result.access_token);
        setReady(true);
        // Fetch notification preferences after session is established.
        getNotificationPreferences()
          .then((prefs) => setNotificationsEnabled(prefs.enabled))
          .catch(() => { /* non-fatal — notifications stay off */ });
      } else {
        // No valid session — redirect to login.
        router.replace("/login");
      }
    });
  }, [pathname, router]);

  async function handleLogout() {
    try {
      await logoutUser();
    } finally {
      clearAccessToken();
      router.replace("/login");
    }
  }

  // Show nothing while we check session on protected pages.
  if (!ready) return null;

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  return (
    <>
      <header className="border-b border-rim bg-white">
        <div className="mx-auto flex max-w-3xl items-center px-6 py-4">
          <Link
            href="/"
            className="text-sm font-semibold tracking-tight text-ink hover:text-accent transition-colors"
          >
            Micro Habit Coach
          </Link>
          {!isPublic && (
            <nav className="ml-auto flex items-center gap-6">
              <Link href="/home" className="text-sm text-ink-muted hover:text-ink transition-colors">
                Today
              </Link>
              <Link href="/habits" className="text-sm text-ink-muted hover:text-ink transition-colors">
                Habits
              </Link>
              <Link href="/history" className="text-sm text-ink-muted hover:text-ink transition-colors">
                History
              </Link>
              <Link href="/schedule" className="text-sm text-ink-muted hover:text-ink transition-colors">
                Schedule
              </Link>
              <Link href="/settings" className="text-sm text-ink-muted hover:text-ink transition-colors">
                Settings
              </Link>
              <button
                onClick={handleLogout}
                className="text-sm text-ink-muted hover:text-ink transition-colors"
              >
                Log out
              </button>
            </nav>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">{children}</main>
    </>
  );
}
