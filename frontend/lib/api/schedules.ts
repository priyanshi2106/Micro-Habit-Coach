import { apiFetch } from "./client";
import type { ScheduleBlock, ScheduleBlockCreate } from "@/lib/types";

export const getScheduleBlocks = (): Promise<ScheduleBlock[]> =>
  apiFetch<ScheduleBlock[]>("/schedule-blocks");

export const createScheduleBlock = (
  body: ScheduleBlockCreate,
): Promise<ScheduleBlock> =>
  apiFetch<ScheduleBlock>("/schedule-blocks", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const deleteScheduleBlock = (id: string): Promise<void> =>
  apiFetch<void>(`/schedule-blocks/${id}`, { method: "DELETE" });
