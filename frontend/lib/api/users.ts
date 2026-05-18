import { apiFetch } from "./client";
import type { User, UserCreate } from "@/lib/types";

export const createUser = (body: UserCreate): Promise<User> =>
  apiFetch<User>("/users", { method: "POST", body: JSON.stringify(body) });

export const getMe = (): Promise<User> => apiFetch<User>("/users/me");
