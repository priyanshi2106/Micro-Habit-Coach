"use client";

import { useCallback, useEffect, useState } from "react";
import { HabitForm } from "@/components/forms/HabitForm";
import { GoalSuggestionPanel } from "@/components/onboarding/GoalSuggestionPanel";
import { Button } from "@/components/ui/Button";
import { getHabits, updateHabit, deleteHabit, getAnchors } from "@/lib/api/habits";
import type { AnchorItem, Habit, HabitCategory } from "@/lib/types";

const CATEGORY_BORDER: Record<HabitCategory, string> = {
  mindfulness: "border-l-violet-300",
  movement: "border-l-orange-300",
  learning: "border-l-blue-300",
  productivity: "border-l-amber-400",
  finance: "border-l-emerald-400",
  social: "border-l-rose-300",
  health: "border-l-teal-400",
};

export default function HabitsPage() {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [anchors, setAnchors] = useState<AnchorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  // Track which habit card has the anchor select open (null = none).
  const [anchorPickerOpen, setAnchorPickerOpen] = useState<string | null>(null);
  // Track per-habit anchor save state.
  const [savingAnchorId, setSavingAnchorId] = useState<string | null>(null);

  const fetchHabits = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, anchorList] = await Promise.all([getHabits(false), getAnchors()]);
      setHabits(data);
      setAnchors(anchorList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load habits");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHabits();
  }, [fetchHabits]);

  async function toggleActive(habit: Habit) {
    // Cancel any pending delete confirmation when toggling
    setConfirmingId(null);
    try {
      const updated = await updateHabit(habit.id, { active: !habit.active });
      setHabits((prev) => prev.map((h) => (h.id === updated.id ? updated : h)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update habit");
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    setConfirmingId(null);
    try {
      await deleteHabit(id);
      setHabits((prev) => prev.filter((h) => h.id !== id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete habit");
    } finally {
      setDeletingId(null);
    }
  }

  async function setAnchor(habit: Habit, key: string | null) {
    setSavingAnchorId(habit.id);
    setAnchorPickerOpen(null);
    try {
      const updated = await updateHabit(habit.id, { anchor_event: key });
      setHabits((prev) => prev.map((h) => (h.id === updated.id ? updated : h)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update anchor");
    } finally {
      setSavingAnchorId(null);
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            Your habits
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
            Habits
          </h1>
        </div>
        <Button variant="ghost" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add habit"}
        </Button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-xl border border-rim bg-white p-6">
          <h2 className="mb-5 text-sm font-semibold text-ink">New habit</h2>

          {/* AI goal path */}
          <GoalSuggestionPanel
            onHabitsSaved={() => {
              setShowForm(false);
              fetchHabits();
            }}
          />

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-rim" />
            <span className="text-xs text-ink-subtle">or browse templates</span>
            <div className="h-px flex-1 bg-rim" />
          </div>

          {/* Template + manual path */}
          <HabitForm
            onSuccess={() => {
              setShowForm(false);
              fetchHabits();
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
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl border border-rim bg-white" />
          ))}
        </div>
      )}

      {!loading && habits.length === 0 && (
        <div className="rounded-xl border border-rim bg-white p-10 text-center">
          <p className="text-sm font-medium text-ink">No habits yet</p>
          <p className="mt-1 text-sm text-ink-muted">
            Click &quot;+ Add habit&quot; to create your first one.
          </p>
        </div>
      )}

      <ul className="flex flex-col gap-2">
        {habits.map((habit) => {
          const currentAnchor = anchors.find((a) => a.key === habit.anchor_event);
          const isPickerOpen = anchorPickerOpen === habit.id;
          const isSavingAnchor = savingAnchorId === habit.id;

          return (
            <li
              key={habit.id}
              className={[
                "rounded-xl border border-rim border-l-4 bg-white px-5 py-4",
                CATEGORY_BORDER[habit.category as HabitCategory] ?? "border-l-rim",
                !habit.active && "opacity-40",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {/* Top row: name + controls */}
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-ink">{habit.name}</p>
                  <p className="mt-0.5 text-xs capitalize text-ink-muted">
                    {habit.category} · {habit.duration_mins} min · {habit.difficulty}
                    {habit.best_time_of_day && ` · ${habit.best_time_of_day}`}
                  </p>
                </div>

                <div className="ml-4 flex items-center gap-4">
                  {/* Delete — quiet text button with inline confirm */}
                  {confirmingId === habit.id ? (
                    <span className="flex items-center gap-2 text-xs">
                      <span className="text-ink-muted">Remove?</span>
                      <button
                        onClick={() => handleDelete(habit.id)}
                        disabled={deletingId === habit.id}
                        className="font-medium text-red-600 hover:text-red-700 disabled:opacity-40 transition-colors"
                      >
                        {deletingId === habit.id ? "Removing…" : "Yes"}
                      </button>
                      <button
                        onClick={() => setConfirmingId(null)}
                        className="text-ink-subtle hover:text-ink transition-colors"
                      >
                        No
                      </button>
                    </span>
                  ) : (
                    <button
                      onClick={() => setConfirmingId(habit.id)}
                      disabled={!!deletingId}
                      className="text-xs text-ink-subtle hover:text-red-600 transition-colors disabled:opacity-40"
                    >
                      Remove
                    </button>
                  )}

                  {/* Active / inactive toggle */}
                  <button
                    onClick={() => toggleActive(habit)}
                    aria-label={habit.active ? "Deactivate habit" : "Activate habit"}
                    className={[
                      "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent",
                      "transition-colors duration-200",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
                      habit.active ? "bg-accent" : "bg-rim",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm",
                        "transition-transform duration-200",
                        habit.active ? "translate-x-4" : "translate-x-0",
                      ].join(" ")}
                    />
                  </button>
                </div>
              </div>

              {/* Anchor row */}
              <div className="mt-2 flex items-center gap-2 text-xs text-ink-subtle">
                {isSavingAnchor ? (
                  <span>Saving…</span>
                ) : isPickerOpen ? (
                  <>
                    <select
                      autoFocus
                      defaultValue={habit.anchor_event ?? ""}
                      onChange={(e) => setAnchor(habit, e.target.value || null)}
                      onBlur={() => setAnchorPickerOpen(null)}
                      className="rounded border border-rim bg-white px-2 py-0.5 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      <option value="">No anchor</option>
                      {anchors.map((a) => (
                        <option key={a.key} value={a.key}>
                          {a.display}
                        </option>
                      ))}
                    </select>
                  </>
                ) : currentAnchor ? (
                  <>
                    <span className="rounded bg-surface px-1.5 py-0.5 text-ink-muted">
                      {currentAnchor.display}
                    </span>
                    <button
                      onClick={() => setAnchorPickerOpen(habit.id)}
                      className="hover:text-ink transition-colors"
                    >
                      change
                    </button>
                    <button
                      onClick={() => setAnchor(habit, null)}
                      className="hover:text-red-500 transition-colors"
                    >
                      ×
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setAnchorPickerOpen(habit.id)}
                    className="hover:text-ink transition-colors"
                  >
                    + Stack with a moment
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
