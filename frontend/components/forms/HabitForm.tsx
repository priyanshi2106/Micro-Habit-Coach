"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { createHabit } from "@/lib/api/habits";
import type { HabitCategory } from "@/lib/types";
import { HABIT_TEMPLATES, CATEGORY_DOT } from "@/lib/constants/habitTemplates";

const CATEGORY_OPTIONS: { value: HabitCategory; label: string }[] = [
  { value: "mindfulness", label: "Mindfulness" },
  { value: "movement", label: "Movement" },
  { value: "learning", label: "Learning" },
  { value: "productivity", label: "Productivity" },
  { value: "finance", label: "Finance" },
  { value: "social", label: "Social" },
  { value: "health", label: "Health" },
];

interface HabitFormProps {
  onSuccess: () => void;
}

export function HabitForm({ onSuccess }: HabitFormProps) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<HabitCategory>("mindfulness");
  const [durationMins, setDurationMins] = useState(5);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyTemplate(t: (typeof HABIT_TEMPLATES)[number]) {
    setName(t.name);
    setCategory(t.category);
    setDurationMins(t.duration_mins);
    setSelectedTemplate(t.name);
  }

  function clearTemplate() {
    setName("");
    setCategory("mindfulness");
    setDurationMins(5);
    setSelectedTemplate(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createHabit({ name, category, duration_mins: durationMins });
      setName("");
      setDurationMins(5);
      setSelectedTemplate(null);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create habit");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Template picker */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
            Start from a template
          </p>
          {selectedTemplate && (
            <button
              type="button"
              onClick={clearTemplate}
              className="text-xs text-ink-subtle hover:text-ink transition-colors"
            >
              ← Clear
            </button>
          )}
        </div>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
          {HABIT_TEMPLATES.map((t) => (
            <button
              key={t.name}
              type="button"
              onClick={() => applyTemplate(t)}
              className={[
                "flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-colors",
                selectedTemplate === t.name
                  ? "border-accent bg-accent-light text-accent"
                  : "border-rim bg-white text-ink hover:border-accent hover:bg-accent-light",
              ].join(" ")}
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${CATEGORY_DOT[t.category]}`} />
              <span className="truncate">{t.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-rim" />
        <span className="text-xs text-ink-subtle">or write your own</span>
        <div className="h-px flex-1 bg-rim" />
      </div>

      {/* Form fields */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label="Habit name"
          value={name}
          onChange={(e) => { setName(e.target.value); setSelectedTemplate(null); }}
          required
          placeholder="e.g. Box breathing"
        />
        <Select
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value as HabitCategory)}
          options={CATEGORY_OPTIONS}
        />
        <Input
          label="Duration (minutes)"
          type="number"
          min={1}
          max={180}
          value={durationMins}
          onChange={(e) => setDurationMins(Number(e.target.value))}
          required
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" loading={submitting}>
          Add habit
        </Button>
      </form>
    </div>
  );
}
