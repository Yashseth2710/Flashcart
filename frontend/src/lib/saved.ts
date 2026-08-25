import { z } from "zod";

import { request } from "./api";
import { saleStatusSchema } from "./sales";

export const savedItemSchema = z.object({
  id: z.string(),
  product_id: z.string(),
  product_name: z.string(),
  product_slug: z.string(),
  image_url: z.string().nullable(),
  brand: z.string().nullable(),
  normal_price: z.string(),
  saved_at: z.string(),

  sale_id: z.string().nullable(),
  sale_name: z.string().nullable(),
  sale_status: saleStatusSchema.nullable(),
  sale_price: z.string().nullable(),
  sale_product_id: z.string().nullable(),
  available_quantity: z.number().nullable(),
  starts_at: z.string().nullable(),
});

export const reminderSchema = z.object({
  id: z.string(),
  sale_id: z.string(),
  sale_name: z.string(),
  description: z.string().nullable(),
  starts_at: z.string(),
  ends_at: z.string(),
  status: saleStatusSchema,
  item_count: z.number(),
  saved_in_sale: z.number(),
});

export const waitingSchema = z.object({
  saved_count: z.number(),
  reminder_count: z.number(),
  open_now: reminderSchema.nullable(),
  opening_next: reminderSchema.nullable(),
});

export type SavedItem = z.infer<typeof savedItemSchema>;
export type Reminder = z.infer<typeof reminderSchema>;
export type Waiting = z.infer<typeof waitingSchema>;

export function fetchSaved(): Promise<SavedItem[]> {
  return request("/saved", z.array(savedItemSchema));
}

export function saveProduct(productId: string): Promise<SavedItem> {
  return request("/saved", savedItemSchema, {
    method: "POST",
    body: { product_id: productId },
  });
}

export function forgetProduct(productId: string): Promise<void> {
  return request(`/saved/${productId}`, z.void(), { method: "DELETE" });
}

export function fetchReminders(): Promise<Reminder[]> {
  return request("/reminders", z.array(reminderSchema));
}

export function remindMe(saleId: string): Promise<Reminder> {
  return request("/reminders", reminderSchema, {
    method: "POST",
    body: { flash_sale_id: saleId },
  });
}

export function forgetSale(saleId: string): Promise<void> {
  return request(`/reminders/${saleId}`, z.void(), { method: "DELETE" });
}

export function fetchWaiting(): Promise<Waiting> {
  return request("/waiting", waitingSchema);
}

/** When a sale opens, phrased the way someone would say it aloud. */
export function opensWhen(startsAt: string): string {
  const start = new Date(startsAt);
  const now = new Date();
  const sameDay = start.toDateString() === now.toDateString();
  const time = start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

  if (sameDay) return `Today, ${time}`;

  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  if (start.toDateString() === tomorrow.toDateString()) return `Tomorrow, ${time}`;

  return `${start.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}, ${time}`;
}
