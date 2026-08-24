import { z } from "zod";

import { request } from "./api";

export const holdStatusSchema = z.enum(["ACTIVE", "COMPLETED", "EXPIRED", "CANCELLED"]);

export const holdSchema = z.object({
  id: z.string(),
  sale_product_id: z.string(),
  quantity: z.number(),
  status: holdStatusSchema,
  expires_at: z.string(),
  seconds_remaining: z.number(),
  created_at: z.string(),

  sale_id: z.string(),
  sale_name: z.string(),
  product_name: z.string(),
  product_slug: z.string(),
  image_url: z.string().nullable(),
  sku: z.string(),
  sale_price: z.string(),
  line_total: z.string(),
});

export type HoldStatus = z.infer<typeof holdStatusSchema>;
export type Hold = z.infer<typeof holdSchema>;

export function fetchHolds(): Promise<Hold[]> {
  return request("/holds", z.array(holdSchema));
}

export function placeHold(input: { sale_product_id: string; quantity: number }): Promise<Hold> {
  return request("/holds", holdSchema, { method: "POST", body: input });
}

export function releaseHold(id: string): Promise<Hold> {
  return request(`/holds/${id}/release`, holdSchema, { method: "POST" });
}

/** Holds still counting down, which are the ones worth acting on. */
export function isLive(hold: Hold): boolean {
  return hold.status === "ACTIVE";
}

/** Minutes and seconds, the way a countdown is read aloud. */
export function formatRemaining(seconds: number): string {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  return `${minutes}:${String(safe % 60).padStart(2, "0")}`;
}
