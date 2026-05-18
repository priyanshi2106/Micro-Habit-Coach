// ---------------------------------------------------------------------------
// Shared TypeScript interfaces — mirror backend Pydantic schemas exactly.
// Import from here everywhere; never inline these shapes in components.
// ---------------------------------------------------------------------------

export type HabitCategory =
  | "mindfulness"
  | "movement"
  | "learning"
  | "productivity"
  | "finance"
  | "social"
  | "health";

export type ScheduleBlockType = "free" | "busy";

export type HabitLogStatus = "done" | "snoozed" | "skipped";

// ---- Entities (read shapes) ------------------------------------------------

export interface User {
  id: string;
  name: string;
  email: string;
  timezone: string;
  created_at: string;
}

export interface Habit {
  id: string;
  user_id: string;
  name: string;
  category: HabitCategory;
  duration_mins: number;
  difficulty: string;
  best_time_of_day: string | null;
  anchor_event: string | null;
  is_custom: boolean;
  active: boolean;
  created_at: string;
}

export interface ScheduleBlock {
  id: string;
  user_id: string;
  day_of_week: number;
  start_time: string; // "HH:MM:SS"
  end_time: string; // "HH:MM:SS"
  block_type: ScheduleBlockType;
}

export interface HabitSnippet {
  id: string;
  name: string;
  category: HabitCategory;
}

export interface HabitSuggestion {
  id: string;
  user_id: string;
  habit_id: string;
  habit: HabitSnippet;
  suggested_window_start: string; // "HH:MM:SS"
  suggested_window_end: string;
  source: string;
  confidence_score: number;
  suggestion_reason: string | null;
  date: string; // "YYYY-MM-DD"
  created_at: string;
}

export interface TodaySuggestionResponse {
  date: string;
  suggestion: HabitSuggestion | null;
  today_log_status: HabitLogStatus | null;
}

export interface HabitLogSummary {
  week_total: number;
  week_done: number;
  week_snoozed: number;
  week_skipped: number;
  current_streak: number;
}

export interface HabitLog {
  id: string;
  user_id: string;
  habit_id: string;
  habit_name: string | null;
  suggestion_id: string | null;
  status: HabitLogStatus;
  completed_at: string | null;
  scheduled_window_start: string | null;
  scheduled_window_end: string | null;
  date: string;
  created_at: string;
}

// ---- Request bodies --------------------------------------------------------

export interface UserCreate {
  name: string;
  email: string;
  timezone: string;
}

export interface HabitCreate {
  name: string;
  category: HabitCategory;
  duration_mins: number;
  difficulty?: string;
}

export interface HabitUpdate {
  name?: string;
  category?: HabitCategory;
  duration_mins?: number;
  active?: boolean;
}

export interface ScheduleBlockCreate {
  day_of_week: number;
  start_time: string; // "HH:MM:SS"
  end_time: string;
  block_type: ScheduleBlockType;
}

export interface HabitLogCreate {
  habit_id: string;
  suggestion_id?: string | null;
  status: HabitLogStatus;
  completed_at?: string | null;
  scheduled_window_start?: string | null;
  scheduled_window_end?: string | null;
  date: string; // "YYYY-MM-DD"
}
