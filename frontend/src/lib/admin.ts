import { z } from "zod";

import { request } from "./api";
import { productDetailSchema, productPageSchema, type ProductPage } from "./catalogue";
import { saleDetailSchema, saleSummarySchema, type SaleDetail, type SaleSummary } from "./sales";

export type { SaleDetail, SaleSummary };

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


export type NewSale = {
  name: string;
  description?: string | null;
  start_time: string;
  end_time: string;
};

export type NewSaleItem = {
  variant_id: string;
  sale_price: string;
  allocated_quantity: number;
  max_per_user: number;
};

export function fetchAllSales(): Promise<SaleSummary[]> {
  return request("/admin/flash-sales", z.array(saleSummarySchema));
}

export function fetchSaleToManage(id: string): Promise<SaleDetail> {
  return request(`/admin/flash-sales/${id}`, saleDetailSchema);
}

export function createSale(body: NewSale): Promise<SaleDetail> {
  return request("/admin/flash-sales", saleDetailSchema, { method: "POST", body });
}

export function addSaleItem(saleId: string, body: NewSaleItem): Promise<SaleDetail> {
  return request(`/admin/flash-sales/${saleId}/items`, saleDetailSchema, {
    method: "POST",
    body,
  });
}

export function removeSaleItem(saleId: string, itemId: string): Promise<SaleDetail> {
  return request(`/admin/flash-sales/${saleId}/items/${itemId}`, saleDetailSchema, {
    method: "DELETE",
  });
}

export function cancelSale(saleId: string): Promise<void> {
  return request(`/admin/flash-sales/${saleId}`, z.void(), { method: "DELETE" });
}
