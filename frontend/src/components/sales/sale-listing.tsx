"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { SaleClock } from "@/components/sales/sale-clock";
import { SaleItemCard } from "@/components/sales/sale-item-card";
import { SaleMarquee } from "@/components/sales/sale-marquee";
import { RemindButton } from "@/components/saved/remind-button";
import { useTurnover } from "@/hooks/use-turnover";
import { fetchSales, type SaleDetail } from "@/lib/sales";

export function SaleListing() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["sales"],
    queryFn: fetchSales,
    // A sale opening or a unit going is worth seeing without a reload.
    refetchInterval: 20_000,
  });

  const running = data?.find((sale) => sale.status === "ACTIVE");
  const coming = data?.filter((sale) => sale.status === "UPCOMING") ?? [];

  // The clock knows the exact second a sale turns over, and waiting for the
  // next poll would leave hold buttons on a sale that has just closed, or hide
  // one that has just opened. Asking the moment it happens closes that window.
  useTurnover(running ?? coming[0]);

  return (
    <>
      {running ? <SaleMarquee sale={running} /> : null}

      <main className="px-6 pb-24 sm:px-12">
        <header className="py-12 lg:py-16">
          <p className="font-script text-2xl leading-none text-ink-soft">Limited runs</p>
          <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em] sm:text-5xl">
            Flash sales
          </h1>
        </header>

        {isError ? (
          <p className="border-l-2 border-reject pl-4 text-sm text-reject">
            Sales could not be loaded. Try again in a moment.
          </p>
        ) : isPending ? (
          <p className="tabular text-sm text-muted">Loading…</p>
        ) : !running && coming.length === 0 ? (
          <Nothing />
        ) : (
          <>
            {running ? <SaleBlock sale={running} isRunning /> : null}
            {coming.map((sale) => (
              <SaleBlock key={sale.id} sale={sale} isRunning={false} />
            ))}
          </>
        )}
      </main>
    </>
  );
}

function SaleBlock({ sale, isRunning }: { sale: SaleDetail; isRunning: boolean }) {
  return (
    <section className="border-t border-rule py-12 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="label text-muted">{isRunning ? "On now" : "Coming up"}</p>
          <h2 className="mt-2 font-display text-3xl uppercase tracking-[0.045em]">{sale.name}</h2>
          {sale.description ? (
            <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
              {sale.description}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col items-end gap-4">
          <SaleClock sale={sale} />
          {!isRunning ? <RemindButton saleId={sale.id} /> : null}
        </div>
      </div>

      {sale.items.length === 0 ? (
        <p className="mt-10 text-sm text-muted">Nothing has been put in this sale yet.</p>
      ) : (
        <div className="mt-10 grid grid-cols-2 gap-x-6 gap-y-12 lg:grid-cols-3 xl:grid-cols-4">
          {sale.items.map((item) => (
            <SaleItemCard key={item.id} item={item} isRunning={isRunning} />
          ))}
        </div>
      )}
    </section>
  );
}

function Nothing() {
  return (
    <div className="py-12">
      <p className="font-display text-2xl text-ink">No sale is running.</p>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
        Sales open for a fixed window with a fixed number of units. Nothing is scheduled right
        now — the shop is still open in the meantime.
      </p>
      <Link
        href="/products"
        className="label mt-8 inline-block border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
      >
        Browse the shop
      </Link>
    </div>
  );
}
