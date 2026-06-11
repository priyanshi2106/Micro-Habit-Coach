"use client";

import type { HabitSuggestion, HabitLogStatus } from "@/lib/types";
import { Button } from "@/components/ui/Button";

interface SuggestionCardProps {
  suggestion: HabitSuggestion | null;
  onAction: (status: HabitLogStatus) => Promise<void>;
  loading?: boolean;
  snoozed?: boolean;
}

function formatTime(raw: string): string {
  const [h, m] = raw.split(":").map(Number);
  const ampm = h < 12 ? "AM" : "PM";
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${ampm}`;
}

export function SuggestionCard({
  suggestion,
  onAction,
  loading = false,
  snoozed = false,
}: SuggestionCardProps) {
  if (!suggestion) {
    return (
      <div className="rounded-xl border border-rim bg-white p-10 text-center">
        <p className="text-sm font-medium text-ink">No suggestion for today</p>
        <p className="mt-2 text-sm text-ink-muted">
          Add at least one habit and a free schedule block that matches today.
        </p>
      </div>
    );
  }

  const { habit, suggested_window_start, suggested_window_end, suggestion_reason, source } =
    suggestion;

  const isAdaptive = source === "adaptive_engine";

  return (
    <div className={[
      "rounded-xl border border-rim bg-white p-8 shadow-sm transition-opacity",
      snoozed && "opacity-60",
    ].filter(Boolean).join(" ")}>
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <span className="inline-block rounded-md bg-accent-light px-2.5 py-1 text-xs font-semibold uppercase tracking-widest text-accent">
          {habit.category}
        </span>
        {isAdaptive && (
          <span className="inline-flex items-center gap-1 rounded-md border border-rim bg-canvas px-2.5 py-1 text-xs text-ink-muted">
            <span aria-hidden>✦</span> Based on your history
          </span>
        )}
      </div>

      <h2 className="text-3xl font-semibold tracking-tight text-ink">
        {habit.name}
      </h2>

      <p className="mt-3 text-sm text-ink-muted">
        {formatTime(suggested_window_start)}
        <span className="mx-1.5 text-ink-subtle">–</span>
        {formatTime(suggested_window_end)}
      </p>

      {suggestion_reason && (
        <p className="mt-5 text-sm leading-relaxed text-ink-muted border-l-2 border-rim pl-4">
          {suggestion_reason}
        </p>
      )}

      {snoozed ? (
        <p className="mt-8 text-sm text-ink-subtle">
          Snoozed — check back later today.
        </p>
      ) : (
        <div className="mt-8 flex flex-wrap gap-2">
          <Button onClick={() => onAction("done")} disabled={loading}>
            Mark done
          </Button>
          <Button variant="ghost" onClick={() => onAction("snoozed")} disabled={loading}>
            Snooze
          </Button>
          <Button variant="ghost" onClick={() => onAction("skipped")} disabled={loading}>
            Skip today
          </Button>
        </div>
      )}
    </div>
  );
}
