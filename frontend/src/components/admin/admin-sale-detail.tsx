"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { SaleClock } from "@/components/sales/sale-clock";
import {
  addSaleItem,
  cancelSale,
  fetchSaleToManage,
  removeSaleItem,
} from "@/lib/admin";
import { ApiError } from "@/lib/api";
import { browseProducts, fetchProduct, formatPrice } from "@/lib/catalogue";

export function AdminSaleDetail({ saleId }: { saleId: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [adding, setAdding] = useState(false);

  const { data: sale, isPending, error } = useQuery({
    queryKey: ["admin-sale", saleId],
    queryFn: () => fetchSaleToManage(saleId),
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 1,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-sale", saleId] });
    queryClient.invalidateQueries({ queryKey: ["admin-sales"] });
    queryClient.invalidateQueries({ queryKey: ["sales"] });
    queryClient.invalidateQueries({ queryKey: ["stock"] });
  };

  const remove = useMutation({
    mutationFn: (itemId: string) => removeSaleItem(saleId, itemId),
    onSuccess: refresh,
  });

  const cancel = useMutation({
    mutationFn: () => cancelSale(saleId),
    onSuccess: () => {
      refresh();
      router.push("/admin/sales");
    },
  });

  if (isPending) {
    return <p className="tabular px-6 py-20 text-sm text-muted sm:px-12">Loading…</p>;
  }

  if (error) {
    return (
      <main className="px-6 py-24 sm:px-12">
        <p className="font-display text-3xl uppercase tracking-[0.045em]">No such sale</p>
        <Link
          href="/admin/sales"
          className="label mt-8 inline-block border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
        >
          Back to sales
        </Link>
      </main>
    );
  }

  const isUpcoming = sale.status === "UPCOMING";

  return (
    <main className="px-6 pb-24 sm:px-12">
      <nav className="py-6">
        <Link href="/admin/sales" className="label text-muted hover:text-ink">
          ← Sales
        </Link>
      </nav>

      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-ink pb-8">
        <div>
          <p className="label text-muted">{sale.status}</p>
          <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">{sale.name}</h1>
          {sale.description ? (
            <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
              {sale.description}
            </p>
          ) : null}
          <p className="tabular mt-4 text-xs text-muted">
            {new Date(sale.start_time).toLocaleString()} —{" "}
            {new Date(sale.end_time).toLocaleString()}
          </p>
        </div>
        <SaleClock sale={sale} />
      </header>

      {!isUpcoming ? (
        <p className="mt-8 max-w-lg border-l-2 border-hold pl-4 text-sm leading-relaxed text-ink-soft">
          {sale.status === "ACTIVE"
            ? "This sale is running. Its products cannot be changed while people are buying from it."
            : "This sale is over. Its products cannot be changed."}
        </p>
      ) : null}

      <div className="mt-12 flex flex-wrap items-baseline justify-between gap-4">
        <h2 className="font-display text-2xl uppercase tracking-[0.045em]">What is in it</h2>
        {isUpcoming ? (
          <button
            onClick={() => setAdding((open) => !open)}
            className="label border border-ink px-7 py-3 transition-colors hover:bg-ink hover:text-paper"
          >
            {adding ? "Cancel" : "Put a product in"}
          </button>
        ) : null}
      </div>

      {adding ? (
        <AddItemForm
          saleId={saleId}
          onDone={() => {
            setAdding(false);
            refresh();
          }}
        />
      ) : null}

      {sale.items.length === 0 ? (
        <p className="mt-8 max-w-md text-sm leading-relaxed text-muted">
          Nothing in this sale yet. Adding a product takes its units out of warehouse stock and
          holds them here until the sale ends.
        </p>
      ) : (
        <div className="mt-8">
          <div className="hidden border-b border-ink pb-3 sm:grid sm:grid-cols-[1fr_7rem_7rem_6rem_6rem_5rem] sm:gap-4">
            {["Product", "Normal", "Sale", "In sale", "Left", ""].map((heading, index) => (
              <p key={index} className="label text-muted">
                {heading}
              </p>
            ))}
          </div>

          {sale.items.map((item) => (
            <div
              key={item.id}
              className="border-b border-rule py-4 sm:grid sm:grid-cols-[1fr_7rem_7rem_6rem_6rem_5rem] sm:items-center sm:gap-4"
            >
              <div>
                <p className="text-sm text-ink">{item.product_name}</p>
                <p className="tabular mt-1 text-xs text-muted">
                  {item.sku} · at most {item.max_per_user} each
                </p>
              </div>
              <p className="tabular mt-2 text-sm text-muted line-through sm:mt-0">
                {formatPrice(item.normal_price)}
              </p>
              <p className="tabular text-sm text-ink">{formatPrice(item.sale_price)}</p>
              <p className="tabular text-sm text-ink-soft">{item.allocated_quantity}</p>
              <p
                className={`tabular text-sm ${
                  item.available_quantity === 0 ? "text-reject" : "text-ink-soft"
                }`}
              >
                {item.available_quantity}
              </p>
              {isUpcoming ? (
                <button
                  onClick={() => remove.mutate(item.id)}
                  disabled={remove.isPending}
                  className="label text-muted transition-colors hover:text-reject"
                >
                  Take out
                </button>
              ) : (
                <span />
              )}
            </div>
          ))}
        </div>
      )}

      {remove.error ? (
        <p role="alert" className="mt-6 border-l-2 border-reject pl-4 text-sm text-reject">
          {remove.error instanceof ApiError ? remove.error.message : "Could not take it out."}
        </p>
      ) : null}

      {isUpcoming ? (
        <div className="mt-16 border-t border-rule pt-8">
          <button
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
            className="label text-muted transition-colors hover:text-reject"
          >
            {cancel.isPending ? "Calling it off" : "Call this sale off"}
          </button>
          <p className="mt-3 max-w-md text-xs leading-relaxed text-muted">
            Everything it holds goes back to warehouse stock.
          </p>
          {cancel.error ? (
            <p role="alert" className="mt-4 border-l-2 border-reject pl-4 text-sm text-reject">
              {cancel.error instanceof ApiError ? cancel.error.message : "Could not call it off."}
            </p>
          ) : null}
        </div>
      ) : null}
    </main>
  );
}

function AddItemForm({ saleId, onDone }: { saleId: string; onDone: () => void }) {
  const [search, setSearch] = useState("");
  const [chosen, setChosen] = useState<{ slug: string; name: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: found } = useQuery({
    queryKey: ["admin-product-search", search],
    queryFn: () => browseProducts({ search, limit: 6 }),
    enabled: search.trim().length > 1 && !chosen,
  });

  const { data: detail } = useQuery({
    queryKey: ["product", chosen?.slug],
    queryFn: () => fetchProduct(chosen!.slug),
    enabled: Boolean(chosen),
  });

  const add = useMutation({
    mutationFn: (body: Parameters<typeof addSaleItem>[1]) => addSaleItem(saleId, body),
    onSuccess: onDone,
  });

  const variant = detail?.variants[0];

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!variant) return;

    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    const found: Record<string, string> = {};

    const price = Number(values.sale_price);
    const quantity = Number(values.allocated_quantity);
    const limit = Number(values.max_per_user);

    if (!Number.isFinite(price) || price < 0) found.sale_price = "Enter a price.";
    if (!Number.isInteger(quantity) || quantity < 1) {
      found.allocated_quantity = "At least one unit.";
    } else if (quantity > variant.available_quantity) {
      found.allocated_quantity = `Only ${variant.available_quantity} in the warehouse.`;
    }
    if (!Number.isInteger(limit) || limit < 1) {
      found.max_per_user = "At least one each.";
    } else if (Number.isInteger(quantity) && limit > quantity) {
      found.max_per_user = "Cannot exceed the allocation.";
    }

    setErrors(found);
    if (Object.keys(found).length > 0) return;

    add.mutate({
      variant_id: variant.id,
      sale_price: price.toFixed(2),
      allocated_quantity: quantity,
      max_per_user: limit,
    });
  }

  return (
    <div className="mt-8 border-y border-rule py-10">
      {!chosen ? (
        <>
          <label className="label block text-muted" htmlFor="sale-item-search">
            Which product
          </label>
          <input
            id="sale-item-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search the catalogue"
            className="mt-2 w-full max-w-sm border-b border-rule bg-transparent pb-2 text-sm outline-none
                       transition-colors placeholder:text-muted/70 focus:border-ink"
          />

          {found && found.items.length > 0 ? (
            <ul className="mt-6 max-w-sm">
              {found.items.map((product) => (
                <li key={product.id}>
                  <button
                    onClick={() => setChosen({ slug: product.slug, name: product.name })}
                    className="flex w-full items-baseline justify-between border-b border-rule py-3 text-left transition-colors hover:text-ink"
                  >
                    <span className="text-sm text-ink-soft">{product.name}</span>
                    <span className="tabular text-xs text-muted">
                      {formatPrice(product.base_price)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : search.trim().length > 1 ? (
            <p className="mt-6 text-sm text-muted">Nothing matches that.</p>
          ) : null}
        </>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <div>
              <p className="label text-muted">Putting in</p>
              <p className="mt-2 font-display text-2xl">{chosen.name}</p>
              <p className="tabular mt-2 text-xs text-muted">
                {variant
                  ? `${variant.available_quantity} in the warehouse · normally ${formatPrice(variant.price)}`
                  : "Reading stock…"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setChosen(null);
                setErrors({});
                add.reset();
              }}
              className="label text-muted hover:text-ink"
            >
              Choose another
            </button>
          </div>

          <div className="mt-8 grid max-w-2xl gap-7 sm:grid-cols-3">
            <Field
              label="Sale price"
              name="sale_price"
              inputMode="decimal"
              defaultValue={variant?.price ?? ""}
              error={errors.sale_price}
            />
            <Field
              label="Units in the sale"
              name="allocated_quantity"
              type="number"
              min={1}
              defaultValue="20"
              error={errors.allocated_quantity}
            />
            <Field
              label="At most each"
              name="max_per_user"
              type="number"
              min={1}
              defaultValue="1"
              error={errors.max_per_user}
            />
          </div>

          {add.error ? (
            <p role="alert" className="mt-6 border-l-2 border-reject pl-4 text-sm text-reject">
              {add.error instanceof ApiError ? add.error.message : "Could not put it in."}
            </p>
          ) : null}

          <Button type="submit" disabled={add.isPending || !variant} className="mt-9">
            {add.isPending ? "Putting in" : "Put it in the sale"}
          </Button>
        </form>
      )}
    </div>
  );
}
