import { z } from "zod";

import { request } from "./api";

export const healthSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  environment: z.string(),
  database: z.enum(["connected", "unreachable", "not_configured"]),
});

export type Health = z.infer<typeof healthSchema>;

export function fetchHealth(): Promise<Health> {
  return request("/health", healthSchema);
}
