"use client";

import { useState } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { createScheduleBlock } from "@/lib/api/schedules";
import type { ScheduleBlockType } from "@/lib/types";

const DAY_OPTIONS = [
  { value: "0", label: "Monday" },
  { value: "1", label: "Tuesday" },
  { value: "2", label: "Wednesday" },
  { value: "3", label: "Thursday" },
  { value: "4", label: "Friday" },
  { value: "5", label: "Saturday" },
  { value: "6", label: "Sunday" },
];

const BLOCK_TYPE_OPTIONS = [
  { value: "free", label: "Free" },
  { value: "busy", label: "Busy" },
];

interface ScheduleBlockFormProps {
  onSuccess: () => void;
}

export function ScheduleBlockForm({ onSuccess }: ScheduleBlockFormProps) {
  const [dayOfWeek, setDayOfWeek] = useState("0");
  const [startTime, setStartTime] = useState("07:00");
  const [endTime, setEndTime] = useState("09:00");
  const [blockType, setBlockType] = useState<ScheduleBlockType>("free");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createScheduleBlock({
        day_of_week: Number(dayOfWeek),
        // Backend expects "HH:MM:SS"; time inputs give "HH:MM"
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
        block_type: blockType,
      });
      onSuccess();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create schedule block",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Select
        label="Day of week"
        value={dayOfWeek}
        onChange={(e) => setDayOfWeek(e.target.value)}
        options={DAY_OPTIONS}
      />
      <div className="flex gap-4">
        <Input
          label="Start time"
          type="time"
          value={startTime}
          onChange={(e) => setStartTime(e.target.value)}
          required
          className="flex-1"
        />
        <Input
          label="End time"
          type="time"
          value={endTime}
          onChange={(e) => setEndTime(e.target.value)}
          required
          className="flex-1"
        />
      </div>
      <Select
        label="Block type"
        value={blockType}
        onChange={(e) => setBlockType(e.target.value as ScheduleBlockType)}
        options={BLOCK_TYPE_OPTIONS}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button type="submit" loading={submitting}>
        Add block
      </Button>
    </form>
  );
}
