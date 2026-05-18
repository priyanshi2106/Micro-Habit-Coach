import type { HabitCategory } from "@/lib/types";

export interface HabitTemplate {
  name: string;
  category: HabitCategory;
  duration_mins: number;
  difficulty: "easy" | "medium" | "hard";
}

export const HABIT_TEMPLATES: HabitTemplate[] = [
  // Mindfulness
  { name: "Box breathing", category: "mindfulness", duration_mins: 5, difficulty: "easy" },
  { name: "Morning meditation", category: "mindfulness", duration_mins: 10, difficulty: "easy" },
  { name: "Gratitude journal", category: "mindfulness", duration_mins: 5, difficulty: "easy" },

  // Movement
  { name: "10-min walk", category: "movement", duration_mins: 10, difficulty: "easy" },
  { name: "Morning stretch", category: "movement", duration_mins: 7, difficulty: "easy" },
  { name: "Evening yoga", category: "movement", duration_mins: 20, difficulty: "medium" },

  // Learning
  { name: "Read 10 pages", category: "learning", duration_mins: 15, difficulty: "easy" },
  { name: "Listen to a podcast", category: "learning", duration_mins: 20, difficulty: "easy" },

  // Productivity
  { name: "Plan tomorrow", category: "productivity", duration_mins: 5, difficulty: "easy" },
  { name: "Review priorities", category: "productivity", duration_mins: 5, difficulty: "easy" },

  // Health
  { name: "Drink 8 glasses of water", category: "health", duration_mins: 1, difficulty: "easy" },
  { name: "Sleep by 10 PM", category: "health", duration_mins: 1, difficulty: "medium" },

  // Finance
  { name: "Track daily spending", category: "finance", duration_mins: 5, difficulty: "easy" },

  // Social
  { name: "Check in with a friend", category: "social", duration_mins: 5, difficulty: "easy" },
];

// Category display colors for template tiles (Tailwind classes, statically known)
export const CATEGORY_DOT: Record<HabitCategory, string> = {
  mindfulness: "bg-violet-300",
  movement: "bg-orange-300",
  learning: "bg-blue-300",
  productivity: "bg-amber-400",
  finance: "bg-emerald-400",
  social: "bg-rose-300",
  health: "bg-teal-400",
};
