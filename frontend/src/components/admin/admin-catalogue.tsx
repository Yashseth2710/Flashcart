"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { NewProductForm } from "@/components/admin/new-product-form";
import { StockRow } from "@/components/admin/stock-row";
import { browseForManagement } from "@/lib/admin";

const PAGE_SIZE = 20;

export function AdminCatalogue() {
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);

  const { data, isPending } = useQuery({
    queryKey: ["admin-products", search],
    queryFn: () => browseForManagement(search || undefined, PAGE_SIZE),
    placeholderData: keepPreviousData,
  });

  return (
    <main className="px-6 pb-24 sm:px-12">
      <header className="flex flex-wrap items-end justify-between gap-6 py-12">
        <div>
          <p className="label text-muted">Manage</p>
          <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Catalogue</h1>
        </div>
        <div className="flex items-center gap-7">
        <Link href="/admin/sales" className="label text-muted hover:text-ink">
          Sales
        </Link>
        <button
          onClick={() => setAdding((open) => !open)}
          className="label border border-ink px-7 py-3 transition-colors hover:bg-ink hover:text-paper"
        >
          {adding ? "Cancel" : "Add a product"}
        </button>
        </div>
      </header>

      {adding ? <NewProductForm onDone={() => setAdding(false)} /> : null}

      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Find a product"
        aria-label="Find a product"
        className="w-full max-w-xs border-b border-rule bg-transparent pb-2 text-sm outline-none
                   transition-colors placeholder:text-muted/70 focus:border-ink"
      />

      <div className="mt-10">
        {isPending || !data ? (
          <p className="tabular text-sm text-muted">Loading…</p>
        ) : data.items.length === 0 ? (
          <p className="py-10 text-sm text-muted">Nothing matches that.</p>
        ) : (
          <>
            <div className="hidden border-b border-ink pb-3 sm:grid sm:grid-cols-[1fr_7rem_7rem_7rem_9rem] sm:gap-4">
              {["Product", "Total", "Held", "Sold", "Available"].map((heading) => (
                <p key={heading} className="label text-muted">
                  {heading}
                </p>
              ))}
            </div>
            {data.items.map((product) => (
              <StockRow key={product.id} product={product} />
            ))}
          </>
        )}
      </div>
    </main>
  );
}
