"use client";

import { useEffect, useState } from "react";
import { getLogs, getSummary } from "@/lib/api/logs";
import type { HabitLog, HabitLogStatus, HabitLogSummary } from "@/lib/types";

const STATUS_STYLES: Record<HabitLogStatus, { label: string; classes: string }> = {
  done: { label: "Done", classes: "bg-accent-light text-accent" },
  snoozed: { label: "Snoozed", classes: "bg-amber-50 text-amber-700" },
  skipped: { label: "Skipped", classes: "bg-stone-100 text-ink-muted" },
};

function formatTime(raw: string): string {
  const [h, m] = raw.split(":").map(Number);
  const ampm = h < 12 ? "AM" : "PM";
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${ampm}`;
}

function formatDate(raw: string): string {
  return new Date(raw).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function formatTimestamp(raw: string): string {
  return new Date(raw).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

// Group logs by calendar_date string, preserving order (newest first).
function groupByDate(logs: HabitLog[]): [string, HabitLog[]][] {
  const map = new Map<string, HabitLog[]>();
  for (const log of logs) {
    const key = log.date;
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(log);
  }
  return Array.from(map.entries());
}

export default function HistoryPage() {
  const [logs, setLogs] = useState<HabitLog[]>([]);
  const [summary, setSummary] = useState<HabitLogSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getLogs(), getSummary()])
      .then(([logsData, summaryData]) => {
        setLogs(logsData);
        setSummary(summaryData);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load history"),
      )
      .finally(() => setLoading(false));
  }, []);

  const grouped = groupByDate(logs);

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Activity
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          History
        </h1>
      </div>

      {summary && (
        <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-rim bg-white px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">Streak</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight text-ink">
              {summary.current_streak}
              <span className="ml-1 text-sm font-normal text-ink-muted">
                {summary.current_streak === 1 ? "day" : "days"}
              </span>
            </p>
          </div>
          <div className="rounded-xl border border-rim bg-white px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">This week</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight text-ink">
              {summary.week_total}
              <span className="ml-1 text-sm font-normal text-ink-muted">logged</span>
            </p>
          </div>
          <div className="rounded-xl border border-accent-light bg-accent-light px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">Done</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight text-accent">
              {summary.week_done}
            </p>
          </div>
          <div className="rounded-xl border border-rim bg-white px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">Skipped</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight text-ink-muted">
              {summary.week_skipped}
            </p>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl border border-rim bg-white" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && logs.length === 0 && (
        <div className="rounded-xl border border-rim bg-white p-10 text-center">
          <p className="text-sm font-medium text-ink">No activity yet</p>
          <p className="mt-1 text-sm text-ink-muted">
            Mark a habit as done, snoozed, or skipped on the Today page to see it here.
          </p>
        </div>
      )}

      {!loading && !error && grouped.length > 0 && (
        <div className="flex flex-col gap-8">
          {grouped.map(([date, entries]) => (
            <section key={date}>
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
                {formatDate(date)}
              </p>
              <ul className="flex flex-col gap-2">
                {entries.map((log) => {
                  const style = STATUS_STYLES[log.status as HabitLogStatus] ?? STATUS_STYLES.skipped;
                  return (
                    <li
                      key={log.id}
                      className="flex items-center justify-between rounded-xl border border-rim bg-white px-5 py-4"
                    >
                      <div>
                        <p className="text-sm font-medium text-ink">{log.habit_name ?? "—"}</p>
                        <p className="mt-0.5 text-xs text-ink-muted">
                          {log.scheduled_window_start && log.scheduled_window_end
                            ? `${formatTime(log.scheduled_window_start)} – ${formatTime(log.scheduled_window_end)}`
                            : formatTimestamp(log.created_at)}
                        </p>
                      </div>
                      <span
                        className={`rounded-md px-2.5 py-1 text-xs font-semibold ${style.classes}`}
                      >
                        {style.label}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
