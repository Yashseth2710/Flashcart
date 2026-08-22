import { z } from "zod";

import { request } from "./api";

export const saleItemSchema = z.object({
  id: z.string(),
  variant_id: z.string(),
  product_name: z.string(),
  product_slug: z.string(),
  image_url: z.string().nullable(),
  sku: z.string(),
  normal_price: z.string(),
  sale_price: z.string(),
  allocated_quantity: z.number(),
  available_quantity: z.number(),
  max_per_user: z.number(),
});

export const saleStatusSchema = z.enum(["UPCOMING", "ACTIVE", "ENDED"]);

export const saleSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  start_time: z.string(),
  end_time: z.string(),
  status: saleStatusSchema,
  item_count: z.number(),
});

export const saleDetailSchema = saleSummarySchema.extend({
  items: z.array(saleItemSchema),
});

export type SaleItem = z.infer<typeof saleItemSchema>;
export type SaleStatus = z.infer<typeof saleStatusSchema>;
export type SaleSummary = z.infer<typeof saleSummarySchema>;
export type SaleDetail = z.infer<typeof saleDetailSchema>;

export function fetchSales(): Promise<SaleDetail[]> {
  return request("/flash-sales", z.array(saleDetailSchema));
}

export function fetchRunningSale(): Promise<SaleDetail | null> {
  return request("/flash-sales/running", saleDetailSchema.nullable());
}

export function fetchSale(id: string): Promise<SaleDetail> {
  return request(`/flash-sales/${id}`, saleDetailSchema);
}

/** How much a sale takes off, for saying so plainly. */
export function discountPercent(normal: string, sale: string): number {
  const before = Number(normal);
  const after = Number(sale);
  if (!Number.isFinite(before) || !Number.isFinite(after) || before <= 0) return 0;
  return Math.round(((before - after) / before) * 100);
}
