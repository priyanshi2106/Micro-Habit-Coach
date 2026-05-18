import { apiFetch } from "./client";
import type { HabitLog, HabitLogCreate, HabitLogSummary } from "@/lib/types";

export const createHabitLog = (body: HabitLogCreate): Promise<HabitLog> =>
  apiFetch<HabitLog>("/habit-logs", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const getLogs = (limit = 50): Promise<HabitLog[]> =>
  apiFetch<HabitLog[]>(`/habit-logs?limit=${limit}`);

export const getSummary = (): Promise<HabitLogSummary> =>
  apiFetch<HabitLogSummary>("/habit-logs/summary");
