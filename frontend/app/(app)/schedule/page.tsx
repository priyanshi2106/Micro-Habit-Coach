"use client";

import { useCallback, useEffect, useState } from "react";
import { ScheduleBlockForm } from "@/components/forms/ScheduleBlockForm";
import { getScheduleBlocks, deleteScheduleBlock } from "@/lib/api/schedules";
import type { ScheduleBlock } from "@/lib/types";

const DAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatTime(raw: string): string {
  const [h, m] = raw.split(":").map(Number);
  const ampm = h < 12 ? "AM" : "PM";
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${ampm}`;
}

export default function SchedulePage() {
  const [blocks, setBlocks] = useState<ScheduleBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchBlocks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setBlocks(await getScheduleBlocks());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load schedule");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBlocks();
  }, [fetchBlocks]);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await deleteScheduleBlock(id);
      setBlocks((prev) => prev.filter((b) => b.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete block");
    } finally {
      setDeletingId(null);
    }
  }

  // Group blocks by day of week for display.
  const byDay = blocks.reduce<Record<number, ScheduleBlock[]>>((acc, b) => {
    (acc[b.day_of_week] ??= []).push(b);
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            Weekly schedule
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
            Schedule
          </h1>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg border border-rim bg-white px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-stone-50"
        >
          {showForm ? "Cancel" : "+ Add block"}
        </button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-xl border border-rim bg-white p-6">
          <h2 className="mb-5 text-sm font-semibold text-ink">New time block</h2>
          <ScheduleBlockForm
            onSuccess={() => {
              setShowForm(false);
              fetchBlocks();
            }}
          />
        </div>
      )}

      {error && (
        <div className="mb-5 rounded-lg border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl border border-rim bg-white" />
          ))}
        </div>
      )}

      {!loading && blocks.length === 0 && (
        <div className="rounded-xl border border-rim bg-white p-10 text-center">
          <p className="text-sm font-medium text-ink">No schedule blocks yet</p>
          <p className="mt-1 text-sm text-ink-muted">
            Add a free time block so the app knows when to suggest habits.
          </p>
        </div>
      )}

      {!loading && blocks.length > 0 && (
        <div className="flex flex-col gap-6">
          {Object.entries(byDay)
            .sort(([a], [b]) => Number(a) - Number(b))
            .map(([day, dayBlocks]) => (
              <section key={day}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
                  {DAY_LABELS[Number(day)]}
                </p>
                <ul className="flex flex-col gap-2">
                  {dayBlocks.map((block) => (
                    <li
                      key={block.id}
                      className="flex items-center justify-between rounded-xl border border-rim bg-white px-5 py-3.5"
                    >
                      <div>
                        <span className="text-sm font-medium text-ink">
                          {formatTime(block.start_time)}
                          <span className="mx-1.5 text-ink-subtle">–</span>
                          {formatTime(block.end_time)}
                        </span>
                        <span className="ml-3 rounded-md bg-stone-100 px-2 py-0.5 text-xs font-medium capitalize text-ink-muted">
                          {block.block_type}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDelete(block.id)}
                        disabled={deletingId === block.id}
                        aria-label="Delete block"
                        className="text-xs text-ink-subtle transition-colors hover:text-red-600 disabled:opacity-40"
                      >
                        {deletingId === block.id ? "Removing…" : "Remove"}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
        </div>
      )}
    </div>
  );
}
