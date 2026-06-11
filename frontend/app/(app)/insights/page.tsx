"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getWeeklyInsight } from "@/lib/api/insights";
import type { WeeklyInsightResponse } from "@/lib/types";

function formatDateRange(start: string, end: string): string {
  const fmt = (d: string) =>
    new Date(d + "T00:00:00").toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
    });
  return `${fmt(start)} – ${fmt(end)}`;
}

function StatPill({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-rim bg-white px-4 py-3 text-center">
      <p className="text-xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-0.5 text-xs text-ink-muted">{label}</p>
    </div>
  );
}

export default function InsightsPage() {
  const [data, setData] = useState<WeeklyInsightResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWeeklyInsight()
      .then(setData)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Could not load insight")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Weekly Insight
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Your week in review
        </h1>
        {data && (
          <p className="mt-1 text-sm text-ink-muted">
            {formatDateRange(data.week_start, data.week_end)}
          </p>
        )}
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4">
          <div className="rounded-xl border border-rim bg-white p-6">
            <div className="h-3 w-20 animate-pulse rounded bg-rim" />
            <div className="mt-4 h-4 w-full animate-pulse rounded bg-rim" />
            <div className="mt-2 h-4 w-5/6 animate-pulse rounded bg-rim" />
            <div className="mt-2 h-4 w-4/6 animate-pulse rounded bg-rim" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-lg border border-rim bg-white"
              />
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-xl border border-red-100 bg-red-50 p-6 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <div className="space-y-6">
          {/* Insight card */}
          <div className="rounded-xl border border-rim bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
                Insight
              </span>
              {data.source === "ai" && (
                <span className="rounded-md border border-rim bg-canvas px-2 py-0.5 text-xs text-ink-muted">
                  AI-generated
                </span>
              )}
            </div>

            {/* No-data / early-stage state */}
            {!data.has_enough_data ? (
              <div>
                <p className="text-sm leading-relaxed text-ink-muted">
                  {data.insight}
                </p>
                <p className="mt-4 text-sm text-ink-subtle">
                  Log habits on the{" "}
                  <Link href="/home" className="text-accent underline-offset-2 hover:underline">
                    Today
                  </Link>{" "}
                  page to build your history.
                </p>
              </div>
            ) : (
              <p className="text-base leading-relaxed text-ink">
                {data.insight}
              </p>
            )}
          </div>

          {/* Stats grid — only show when there is meaningful data */}
          {data.has_enough_data && (
            <div className="grid grid-cols-3 gap-3">
              <StatPill label="Done" value={data.stats.done} />
              <StatPill label="Snoozed" value={data.stats.snoozed} />
              <StatPill label="Skipped" value={data.stats.skipped} />
            </div>
          )}

          {/* Highlights row — best/worst info when available */}
          {data.has_enough_data &&
            (data.stats.best_day || data.stats.most_skipped_habit) && (
              <div className="rounded-xl border border-rim bg-white p-5 text-sm">
                {data.stats.best_day && (
                  <p className="text-ink-muted">
                    <span className="font-medium text-ink">Best day: </span>
                    {data.stats.best_day}
                  </p>
                )}
                {data.stats.best_habit && (
                  <p className="mt-2 text-ink-muted">
                    <span className="font-medium text-ink">Top habit: </span>
                    {data.stats.best_habit}
                  </p>
                )}
                {data.stats.most_skipped_habit && (
                  <p className="mt-2 text-ink-muted">
                    <span className="font-medium text-ink">Most skipped: </span>
                    {data.stats.most_skipped_habit}
                  </p>
                )}
              </div>
            )}
        </div>
      )}
    </div>
  );
}
