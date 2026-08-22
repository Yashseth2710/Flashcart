"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { fetchStock, setStock } from "@/lib/admin";
import { formatPrice, type ProductSummary } from "@/lib/catalogue";

export function StockRow({ product }: { product: ProductSummary }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<string | null>(null);
  const [amount, setAmount] = useState("");

  const { data: levels = [] } = useQuery({
    queryKey: ["stock", product.id],
    queryFn: () => fetchStock(product.id),
  });

  const save = useMutation({
    mutationFn: ({ variantId, total }: { variantId: string; total: number }) =>
      setStock(variantId, total),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stock", product.id] });
      setEditing(null);
    },
  });

  return (
    <div className="border-b border-rule py-4">
      {levels.map((level) => (
        <div
          key={level.variant_id}
          className="sm:grid sm:grid-cols-[1fr_7rem_7rem_7rem_9rem] sm:items-center sm:gap-4"
        >
          <div>
            <p className="text-sm text-ink">{product.name}</p>
            <p className="tabular mt-1 text-xs text-muted">
              {level.sku} · {formatPrice(product.base_price)}
            </p>
          </div>

          {editing === level.variant_id ? (
            <form
              className="col-span-4 mt-3 flex items-center gap-3 sm:mt-0"
              onSubmit={(event) => {
                event.preventDefault();
                const total = Number(amount);
                if (Number.isInteger(total) && total >= 0) {
                  save.mutate({ variantId: level.variant_id, total });
                }
              }}
            >
              <input
                type="number"
                min={0}
                value={amount}
                autoFocus
                onChange={(event) => setAmount(event.target.value)}
                aria-label={`Total stock for ${level.sku}`}
                className="tabular w-24 border-b border-ink bg-transparent pb-1 text-sm outline-none"
              />
              <button type="submit" disabled={save.isPending} className="label text-ink underline underline-offset-4">
                {save.isPending ? "Saving" : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditing(null);
                  save.reset();
                }}
                className="label text-muted hover:text-ink"
              >
                Cancel
              </button>
              {save.error ? (
                <span role="alert" className="text-xs text-reject">
                  {save.error instanceof ApiError ? save.error.message : "Could not save."}
                </span>
              ) : null}
            </form>
          ) : (
            <>
              <Figure value={level.total_quantity} />
              <Figure value={level.reserved_quantity} tone={level.reserved_quantity > 0 ? "hold" : undefined} />
              <Figure value={level.sold_quantity} tone={level.sold_quantity > 0 ? "fill" : undefined} />
              <div className="mt-2 flex items-center gap-4 sm:mt-0">
                <Figure value={level.available_quantity} tone={level.available_quantity === 0 ? "reject" : undefined} />
                <button
                  onClick={() => {
                    setEditing(level.variant_id);
                    setAmount(String(level.total_quantity));
                  }}
                  className="label text-muted hover:text-ink"
                >
                  Edit
                </button>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function Figure({ value, tone }: { value: number; tone?: "hold" | "fill" | "reject" }) {
  const colour = tone ? { hold: "text-hold", fill: "text-fill", reject: "text-reject" }[tone] : "text-ink-soft";
  return <p className={`tabular text-sm ${colour}`}>{value}</p>;
}
