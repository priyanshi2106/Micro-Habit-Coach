"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SuggestionCard } from "@/components/cards/SuggestionCard";
import { getTodaySuggestion } from "@/lib/api/suggestions";
import { createHabitLog } from "@/lib/api/logs";
import type { HabitSuggestion, HabitLogStatus } from "@/lib/types";

export default function HomePage() {
  const [suggestion, setSuggestion] = useState<HabitSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [lastAction, setLastAction] = useState<HabitLogStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestion = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTodaySuggestion();
      setSuggestion(data.suggestion);
      // Restore resolved state from the server so navigation doesn't reset the UI.
      if (data.today_log_status) {
        setLastAction(data.today_log_status);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Could not load suggestion",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSuggestion();
  }, [fetchSuggestion]);

  async function handleAction(status: HabitLogStatus) {
    if (!suggestion) return;
    setActing(true);
    try {
      await createHabitLog({
        habit_id: suggestion.habit_id,
        suggestion_id: suggestion.id,
        status,
        completed_at: status === "done" ? new Date().toISOString() : null,
        scheduled_window_start: suggestion.suggested_window_start,
        scheduled_window_end: suggestion.suggested_window_end,
        date: suggestion.date,
      });
      setLastAction(status);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to log action");
    } finally {
      setActing(false);
    }
  }

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const resolved = lastAction === "done" || lastAction === "skipped";

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          {today}
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Your habit for today
        </h1>
      </div>

      {loading && (
        <div className="rounded-xl border border-rim bg-white p-8">
          <div className="h-4 w-24 animate-pulse rounded bg-rim" />
          <div className="mt-4 h-8 w-48 animate-pulse rounded bg-rim" />
          <div className="mt-3 h-3 w-32 animate-pulse rounded bg-rim" />
          <div className="mt-8 flex gap-2">
            <div className="h-9 w-24 animate-pulse rounded-lg bg-rim" />
            <div className="h-9 w-20 animate-pulse rounded-lg bg-rim" />
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Weekly insight teaser — shown once suggestion has loaded */}
          <div className="mb-6">
            <Link
              href="/insights"
              className="flex items-center justify-between rounded-xl border border-rim bg-white px-5 py-3.5 text-sm transition-colors hover:border-accent hover:bg-accent-light"
            >
              <span className="text-ink-muted">
                <span className="font-medium text-ink">Weekly Insight</span>
                {" "}— see how your week went
              </span>
              <span className="text-ink-subtle">→</span>
            </Link>
          </div>

          {/* Done or Skipped — resolved state replaces the card */}
          {resolved && suggestion && (
            <div className="rounded-xl border border-rim bg-white px-8 py-10 text-center">
              <p className="text-2xl">
                {lastAction === "done" ? "✓" : "·"}
              </p>
              <p className="mt-3 text-base font-semibold text-ink">
                {lastAction === "done"
                  ? "Nice work."
                  : "Skipped for today."}
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                {suggestion.habit.name}
              </p>
              <p className="mt-4 text-xs text-ink-subtle">
                {lastAction === "done"
                  ? "Come back tomorrow for your next habit."
                  : "No worries — a fresh suggestion awaits tomorrow."}
              </p>
            </div>
          )}

          {/* Snoozed — card stays but buttons are replaced */}
          {lastAction === "snoozed" && (
            <SuggestionCard
              suggestion={suggestion}
              onAction={handleAction}
              loading={acting}
              snoozed
            />
          )}

          {/* Default — actionable card */}
          {lastAction === null && (
            <SuggestionCard
              suggestion={suggestion}
              onAction={handleAction}
              loading={acting}
            />
          )}
        </>
      )}
    </div>
  );
}
