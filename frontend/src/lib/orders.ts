import { z } from "zod";

import { request } from "./api";

export const orderStatusSchema = z.enum(["PAID", "FULFILLED", "CANCELLED"]);

export const orderLineSchema = z.object({
  id: z.string(),
  product_name: z.string(),
  price: z.string(),
  quantity: z.number(),
  line_total: z.string(),
  product_slug: z.string().nullable(),
  image_url: z.string().nullable(),
});

export const orderSchema = z.object({
  id: z.string(),
  status: orderStatusSchema,
  subtotal: z.string(),
  total: z.string(),
  placed_at: z.string(),
  sale_name: z.string().nullable(),
  items: z.array(orderLineSchema),
});

export type OrderStatus = z.infer<typeof orderStatusSchema>;
export type OrderLine = z.infer<typeof orderLineSchema>;
export type Order = z.infer<typeof orderSchema>;

export function fetchOrders(): Promise<Order[]> {
  return request("/orders", z.array(orderSchema));
}

export function fetchOrder(id: string): Promise<Order> {
  return request(`/orders/${id}`, orderSchema);
}

export function checkOut(input: {
  reservation_id: string;
  idempotency_key: string;
  card_number?: string;
}): Promise<Order> {
  return request("/orders", orderSchema, { method: "POST", body: input });
}

/** A key for one attempt at buying one hold.
 *
 * Held still across retries of the same checkout, so a dropped connection or an
 * impatient second tap settles as one order rather than two. */
export function keyForCheckout(reservationId: string): string {
  return `checkout-${reservationId}-${crypto.randomUUID()}`;
}

/** An order reference short enough to read aloud, from the id it belongs to. */
export function shortReference(id: string): string {
  return id.replace(/-/g, "").slice(0, 8).toUpperCase();
}
