import { z } from "zod";

import { request } from "./api";

export const profileSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string(),
  role: z.enum(["CUSTOMER", "ADMIN"]),
  created_at: z.string(),
});

export type Profile = z.infer<typeof profileSchema>;

export type Credentials = { email: string; password: string };
export type Registration = Credentials & { name: string };

export function fetchProfile(): Promise<Profile> {
  return request("/auth/me", profileSchema);
}

export function login(body: Credentials): Promise<Profile> {
  return request("/auth/login", profileSchema, { method: "POST", body });
}

export function register(body: Registration): Promise<Profile> {
  return request("/auth/register", profileSchema, { method: "POST", body });
}

export function logout(): Promise<void> {
  return request("/auth/logout", z.void(), { method: "POST" });
}
