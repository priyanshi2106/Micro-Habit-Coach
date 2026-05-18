import { apiFetch } from "./client";
import type { TodaySuggestionResponse } from "@/lib/types";

export const getTodaySuggestion = (): Promise<TodaySuggestionResponse> =>
  apiFetch<TodaySuggestionResponse>("/suggestions/today");
