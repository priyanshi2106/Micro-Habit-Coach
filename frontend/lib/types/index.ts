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
  /** Valid anchor key from GET /anchors, or null to clear. */
  anchor_event?: string | null;
}

export interface AnchorItem {
  key: string;
  display: string;
}

export interface CalendarConnection {
  id: string;
  user_id: string;
  provider: string;
  google_account_email: string;
  is_active: boolean;
  connected_at: string;
  last_synced_at: string | null;
}

export interface CalendarStatusResponse {
  connected: boolean;
  connection: CalendarConnection | null;
}

export interface NotificationPreference {
  id: string | null;
  user_id: string | null;
  enabled: boolean;
  notify_minutes_before: number;
  confidence_threshold: number;
  last_acknowledged_at: string | null;
}

export interface NotificationPreferenceUpdate {
  enabled: boolean;
  notify_minutes_before: number;
  confidence_threshold: number;
}

export interface NotificationPendingResponse {
  should_notify: boolean;
  habit_name: string | null;
  habit_duration_mins: number | null;
  window_start: string | null;
  window_end: string | null;
  suggestion_reason: string | null;
  confidence_score: number | null;
}

/** Maps confidence_threshold floats to UI labels. */
export const CONFIDENCE_LEVEL_LABELS: Record<number, string> = {
  0.45: "Any",
  0.65: "Medium",
  0.80: "High",
};

export interface ScheduleBlockCreate {
  day_of_week: number;
  start_time: string; // "HH:MM:SS"
  end_time: string;
  block_type: ScheduleBlockType;
}

export interface HabitSuggestionDraft {
  name: string;
  category: HabitCategory;
  duration_mins: number;
  reason: string;
}

export interface GoalSuggestionResponse {
  suggestions: HabitSuggestionDraft[];
  source: "ai" | "fallback";
  goal: string;
}

export interface WeeklyStats {
  total: number;
  done: number;
  snoozed: number;
  skipped: number;
  completion_rate: number;
  best_day: string | null;
  worst_day: string | null;
  best_habit: string | null;
  most_skipped_habit: string | null;
}

export interface WeeklyInsightResponse {
  week_start: string; // "YYYY-MM-DD"
  week_end: string;
  stats: WeeklyStats;
  insight: string;
  source: "ai" | "fallback";
  // False when there is not yet enough log history for a meaningful insight.
  // Use this instead of hardcoding stats.total thresholds in the UI.
  has_enough_data: boolean;
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
