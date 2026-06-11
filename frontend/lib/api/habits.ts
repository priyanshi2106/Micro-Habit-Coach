import { apiFetch } from "./client";
import type { AnchorItem, Habit, HabitCreate, HabitUpdate, GoalSuggestionResponse } from "@/lib/types";

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

export const getGoalSuggestions = (goal: string): Promise<GoalSuggestionResponse> =>
  apiFetch<GoalSuggestionResponse>("/onboarding/goal-suggestions", {
    method: "POST",
    body: JSON.stringify({ goal }),
  });

/** Fetch the static anchor catalog (key + display label). No auth required. */
export const getAnchors = (): Promise<AnchorItem[]> =>
  apiFetch<AnchorItem[]>("/anchors");
