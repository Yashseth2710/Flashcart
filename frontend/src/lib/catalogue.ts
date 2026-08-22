import { z } from "zod";

import { request } from "./api";

export const productSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  category: z.string().nullable(),
  brand: z.string().nullable(),
  image_url: z.string().nullable(),
  base_price: z.string(),
});

export const variantSchema = z.object({
  id: z.string(),
  sku: z.string(),
  name: z.string(),
  price: z.string(),
  available_quantity: z.number(),
});

export const productDetailSchema = productSummarySchema.extend({
  description: z.string().nullable(),
  is_active: z.boolean(),
  variants: z.array(variantSchema),
});

export const productPageSchema = z.object({
  items: z.array(productSummarySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type ProductSummary = z.infer<typeof productSummarySchema>;
export type ProductDetail = z.infer<typeof productDetailSchema>;
export type ProductPage = z.infer<typeof productPageSchema>;

export type BrowseFilters = {
  search?: string;
  category?: string;
  limit?: number;
  offset?: number;
};

export function browseProducts(filters: BrowseFilters = {}): Promise<ProductPage> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.category) params.set("category", filters.category);
  params.set("limit", String(filters.limit ?? 24));
  params.set("offset", String(filters.offset ?? 0));

  return request(`/products?${params}`, productPageSchema);
}

export function fetchProduct(slug: string): Promise<ProductDetail> {
  return request(`/products/${encodeURIComponent(slug)}`, productDetailSchema);
}

export function fetchCategories(): Promise<string[]> {
  return request("/products/categories", z.array(z.string()));
}

/** Prices arrive as strings so nothing is rounded before it is shown, and the
 *  pence are kept because a shop that hides them looks careless. */
export function formatPrice(amount: string): string {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return amount;
  }
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}
