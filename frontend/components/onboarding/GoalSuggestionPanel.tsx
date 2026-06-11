"use client";

import { useState } from "react";
import { getGoalSuggestions } from "@/lib/api/habits";
import { createHabit } from "@/lib/api/habits";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { HabitCategory, HabitSuggestionDraft } from "@/lib/types";

/** Must match ALLOWED_DURATIONS in backend/app/modules/ai/schemas.py */
const ALLOWED_DURATIONS = [5, 10, 15, 20, 30] as const;

// ── Types ────────────────────────────────────────────────────────────────────

type PanelState = "idle" | "loading" | "review" | "saved";

interface DraftCard {
  id: string; // local key only, not sent to backend
  name: string;
  category: HabitCategory;
  duration_mins: number;
  reason: string;
  dismissed: boolean;
  saveError: string | null;
}

interface Props {
  onHabitsSaved: (count: number) => void;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const CATEGORY_OPTIONS: { value: HabitCategory; label: string }[] = [
  { value: "mindfulness", label: "Mindfulness" },
  { value: "movement", label: "Movement" },
  { value: "learning", label: "Learning" },
  { value: "productivity", label: "Productivity" },
  { value: "finance", label: "Finance" },
  { value: "social", label: "Social" },
  { value: "health", label: "Health" },
];

const DURATION_OPTIONS = ALLOWED_DURATIONS.map((d) => ({
  value: String(d),
  label: `${d} min`,
}));

function draftsFromSuggestions(suggestions: HabitSuggestionDraft[]): DraftCard[] {
  return suggestions.map((s, i) => ({
    id: `${i}-${s.name}`,
    name: s.name,
    category: s.category,
    duration_mins: s.duration_mins,
    reason: s.reason,
    dismissed: false,
    saveError: null,
  }));
}

// ── Component ────────────────────────────────────────────────────────────────

export function GoalSuggestionPanel({ onHabitsSaved }: Props) {
  const [panelState, setPanelState] = useState<PanelState>("idle");
  const [goal, setGoal] = useState("");
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [source, setSource] = useState<"ai" | "fallback" | null>(null);
  const [cards, setCards] = useState<DraftCard[]>([]);
  const [saving, setSaving] = useState(false);

  const activeCards = cards.filter((c) => !c.dismissed);
  const pendingCards = activeCards.filter((c) => c.saveError !== null);

  // ── Generate ───────────────────────────────────────────────────────────────

  async function handleGenerate() {
    if (!goal.trim() || panelState === "loading") return;
    setFetchError(null);
    setPanelState("loading");
    try {
      const res = await getGoalSuggestions(goal.trim());
      setSource(res.source);
      setCards(draftsFromSuggestions(res.suggestions));
      setPanelState("review");
    } catch (err: unknown) {
      setFetchError(
        err instanceof Error ? err.message : "Could not fetch suggestions."
      );
      setPanelState("idle");
    }
  }

  // ── Card edits ─────────────────────────────────────────────────────────────

  function updateCard(id: string, patch: Partial<DraftCard>) {
    setCards((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...patch } : c))
    );
  }

  // ── Save (Promise.allSettled — partial failure safe) ──────────────────────

  async function handleSave() {
    // activeCards already excludes dismissed (successfully saved) cards.
    // On first save: all active cards have no error → all are saved.
    // On retry: only failed cards remain active → only failed cards are retried.
    const toSave = activeCards;
    if (toSave.length === 0) return;

    setSaving(true);

    // Clear previous errors only on cards we're about to retry.
    setCards((prev) =>
      prev.map((c) =>
        toSave.find((t) => t.id === c.id) ? { ...c, saveError: null } : c
      )
    );

    const results = await Promise.allSettled(
      toSave.map((card) =>
        createHabit({
          name: card.name,
          category: card.category,
          duration_mins: card.duration_mins,
          difficulty: "easy",
        })
      )
    );

    let saved = 0;
    const updates: Record<string, string | null> = {};

    results.forEach((result, i) => {
      const card = toSave[i];
      if (result.status === "fulfilled") {
        updates[card.id] = "dismiss"; // mark for removal
        saved++;
      } else {
        const msg =
          result.reason instanceof Error
            ? result.reason.message
            : "Could not save — try again";
        updates[card.id] = msg;
      }
    });

    setCards((prev) =>
      prev.map((c) => {
        const update = updates[c.id];
        if (update === undefined) return c;
        if (update === "dismiss") return { ...c, dismissed: true, saveError: null };
        return { ...c, saveError: update };
      })
    );

    setSaving(false);

    if (saved > 0) {
      onHabitsSaved(saved);
      // If all selected habits saved successfully, show the confirmation state.
      const anyFailed = results.some((r) => r.status === "rejected");
      if (!anyFailed) setPanelState("saved");
    }
  }

  // ── Reset ──────────────────────────────────────────────────────────────────

  function handleReset() {
    setGoal("");
    setCards([]);
    setSource(null);
    setFetchError(null);
    setPanelState("idle");
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  const retryCount = pendingCards.length;
  const saveLabel =
    retryCount > 0
      ? `Retry ${retryCount} failed habit${retryCount > 1 ? "s" : ""}`
      : activeCards.length === 0
      ? "No habits selected"
      : `Add ${activeCards.length} habit${activeCards.length > 1 ? "s" : ""}`;

  return (
    <div className="flex flex-col gap-4">
      {/* ── Goal input ─────────────────────────────────────────────────── */}
      {(panelState === "idle" || panelState === "loading") && (
        <div className="flex flex-col gap-3">
          <Input
            label="What do you want to work on?"
            placeholder="e.g. sleep better, reduce stress, be more active"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleGenerate();
              }
            }}
          />
          {fetchError && (
            <p className="text-xs text-red-600">{fetchError}</p>
          )}
          <Button
            onClick={handleGenerate}
            loading={panelState === "loading"}
            disabled={!goal.trim() || panelState === "loading"}
          >
            {panelState === "loading"
              ? `Finding habits for "${goal}"…`
              : "Generate my starter habits"}
          </Button>
        </div>
      )}

      {/* ── Saved confirmation ─────────────────────────────────────────── */}
      {panelState === "saved" && (
        <div className="flex items-center justify-between rounded-xl border border-accent-light bg-accent-light px-5 py-4">
          <p className="text-sm font-medium text-accent">
            Habits added — you&apos;re all set.
          </p>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-accent underline hover:no-underline"
          >
            Add more
          </button>
        </div>
      )}

      {/* ── Review cards ───────────────────────────────────────────────── */}
      {panelState === "review" && (
        <div className="flex flex-col gap-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
                Suggested for
              </p>
              <p className="mt-0.5 text-sm font-semibold text-ink">
                &ldquo;{goal}&rdquo;
              </p>
              {source === "fallback" && (
                <p className="mt-0.5 text-xs text-ink-subtle">
                  Using starter templates — AI unavailable right now.
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-ink-subtle transition-colors hover:text-ink"
            >
              ← Try again
            </button>
          </div>

          {/* Cards */}
          {activeCards.length === 0 ? (
            <p className="text-sm text-ink-muted">
              All suggestions dismissed. Add habits below or{" "}
              <button
                type="button"
                onClick={handleReset}
                className="underline hover:text-ink"
              >
                try a different goal
              </button>
              .
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {activeCards.map((card) => (
                <li
                  key={card.id}
                  className="rounded-xl border border-rim bg-white p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex flex-1 flex-col gap-2">
                      {/* Name */}
                      <input
                        type="text"
                        value={card.name}
                        onChange={(e) =>
                          updateCard(card.id, { name: e.target.value })
                        }
                        className="w-full rounded-md border border-rim bg-canvas px-3 py-1.5 text-sm font-medium text-ink focus:border-accent focus:outline-none"
                      />

                      {/* Category + Duration */}
                      <div className="flex gap-2">
                        <select
                          value={card.category}
                          onChange={(e) =>
                            updateCard(card.id, {
                              category: e.target.value as HabitCategory,
                            })
                          }
                          className="flex-1 rounded-md border border-rim bg-white px-2 py-1.5 text-xs text-ink focus:border-accent focus:outline-none"
                        >
                          {CATEGORY_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>

                        <select
                          value={String(card.duration_mins)}
                          onChange={(e) =>
                            updateCard(card.id, {
                              duration_mins: Number(e.target.value),
                            })
                          }
                          className="w-24 rounded-md border border-rim bg-white px-2 py-1.5 text-xs text-ink focus:border-accent focus:outline-none"
                        >
                          {DURATION_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Reason */}
                      <p className="text-xs italic leading-relaxed text-ink-subtle">
                        {card.reason}
                      </p>

                      {/* Save error */}
                      {card.saveError && (
                        <p className="text-xs text-red-600">{card.saveError}</p>
                      )}
                    </div>

                    {/* Dismiss */}
                    <button
                      type="button"
                      onClick={() => updateCard(card.id, { dismissed: true })}
                      aria-label="Dismiss suggestion"
                      className="mt-0.5 text-ink-subtle transition-colors hover:text-red-500"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {/* Save button */}
          {activeCards.length > 0 && (
            <Button
              onClick={handleSave}
              loading={saving}
              disabled={saving || activeCards.length === 0}
            >
              {saveLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
