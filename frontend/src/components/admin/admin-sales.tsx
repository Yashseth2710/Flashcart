"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { NewSaleForm } from "@/components/admin/new-sale-form";
import { fetchAllSales, type SaleSummary } from "@/lib/admin";

const tone: Record<SaleSummary["status"], string> = {
  ACTIVE: "text-hold",
  UPCOMING: "text-ink",
  ENDED: "text-muted",
};

export function AdminSales() {
  const [adding, setAdding] = useState(false);
  const { data, isPending } = useQuery({ queryKey: ["admin-sales"], queryFn: fetchAllSales });

  return (
    <main className="px-6 pb-24 sm:px-12">
      <header className="flex flex-wrap items-end justify-between gap-6 py-12">
        <div>
          <p className="label text-muted">Manage</p>
          <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Sales</h1>
        </div>
        <div className="flex items-center gap-7">
          <Link href="/admin" className="label text-muted hover:text-ink">
            Catalogue
          </Link>
          <button
            onClick={() => setAdding((open) => !open)}
            className="label border border-ink px-7 py-3 transition-colors hover:bg-ink hover:text-paper"
          >
            {adding ? "Cancel" : "Plan a sale"}
          </button>
        </div>
      </header>

      {adding ? <NewSaleForm onDone={() => setAdding(false)} /> : null}

      {isPending || !data ? (
        <p className="tabular text-sm text-muted">Loading…</p>
      ) : data.length === 0 ? (
        <p className="py-10 max-w-md text-sm leading-relaxed text-muted">
          No sales yet. A sale runs for a fixed window and holds a set number of units, taken
          out of warehouse stock while it lasts.
        </p>
      ) : (
        <>
          <div className="hidden border-b border-ink pb-3 sm:grid sm:grid-cols-[1fr_8rem_12rem_6rem] sm:gap-4">
            {["Sale", "Status", "Window", "Items"].map((heading) => (
              <p key={heading} className="label text-muted">
                {heading}
              </p>
            ))}
          </div>
          {data.map((sale) => (
            <Link
              key={sale.id}
              href={`/admin/sales/${sale.id}`}
              className="block border-b border-rule py-4 transition-colors hover:bg-panel/60 sm:grid sm:grid-cols-[1fr_8rem_12rem_6rem] sm:items-baseline sm:gap-4"
            >
              <p className="text-sm text-ink">{sale.name}</p>
              <p className={`label mt-1 sm:mt-0 ${tone[sale.status]}`}>{sale.status}</p>
              <p className="tabular mt-1 text-xs text-muted sm:mt-0">
                {new Date(sale.start_time).toLocaleString()} 
              </p>
              <p className="tabular mt-1 text-xs text-ink-soft sm:mt-0">{sale.item_count}</p>
            </Link>
          ))}
        </>
      )}
    </main>
  );
}
