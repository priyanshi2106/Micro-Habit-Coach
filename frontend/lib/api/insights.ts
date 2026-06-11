import { apiFetch } from "./client";
import type { WeeklyInsightResponse } from "@/lib/types";

export const getWeeklyInsight = (): Promise<WeeklyInsightResponse> =>
  apiFetch<WeeklyInsightResponse>("/insights/weekly");
