import { z } from "zod";

import { request } from "./api";
import { productDetailSchema, productPageSchema, type ProductPage } from "./catalogue";

export const stockLevelSchema = z.object({
  variant_id: z.string(),
  sku: z.string(),
  total_quantity: z.number(),
  reserved_quantity: z.number(),
  sold_quantity: z.number(),
  available_quantity: z.number(),
});

export type StockLevel = z.infer<typeof stockLevelSchema>;

/** The manage screen shows hidden products too, newest first, so something
 *  just added is at the top rather than buried alphabetically. */
export function browseForManagement(search?: string, limit = 20): Promise<ProductPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (search) params.set("search", search);
  return request(`/admin/products?${params}`, productPageSchema);
}

export type NewProduct = {
  name: string;
  category?: string | null;
  brand?: string | null;
  image_url?: string | null;
  base_price: string;
};

export function createProduct(body: NewProduct) {
  return request("/admin/products", productDetailSchema, { method: "POST", body });
}

export function updateProduct(id: string, body: Record<string, unknown>) {
  return request(`/admin/products/${id}`, productDetailSchema, { method: "PATCH", body });
}

export function fetchStock(productId: string): Promise<StockLevel[]> {
  return request(`/admin/products/${productId}/stock`, z.array(stockLevelSchema));
}

export function setStock(variantId: string, total: number): Promise<StockLevel> {
  return request("/admin/stock", stockLevelSchema, {
    method: "PUT",
    body: { variant_id: variantId, total_quantity: total },
  });
}
