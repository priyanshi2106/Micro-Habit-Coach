import { apiFetch } from "./client";
import type { Habit, HabitCreate, HabitUpdate } from "@/lib/types";

export const getHabits = (activeOnly = false): Promise<Habit[]> =>
  apiFetch<Habit[]>(`/habits?active_only=${activeOnly}`);

export const createHabit = (body: HabitCreate): Promise<Habit> =>
  apiFetch<Habit>("/habits", { method: "POST", body: JSON.stringify(body) });

export const updateHabit = (id: string, body: HabitUpdate): Promise<Habit> =>
  apiFetch<Habit>(`/habits/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteHabit = (id: string): Promise<void> =>
  apiFetch<void>(`/habits/${id}`, { method: "DELETE" });
