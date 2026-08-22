"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { SaleClock } from "@/components/sales/sale-clock";
import { SaleItemCard } from "@/components/sales/sale-item-card";
import { SaleMarquee } from "@/components/sales/sale-marquee";
import { fetchSales } from "@/lib/sales";

/** The front page leads with whatever is happening: a sale on now, one coming,
 *  or the plain shop when there is neither. */
export function FrontPageSale() {
  const { data } = useQuery({
    queryKey: ["sales"],
    queryFn: fetchSales,
    refetchInterval: 20_000,
  });

  const running = data?.find((sale) => sale.status === "ACTIVE");
  const next = data?.find((sale) => sale.status === "UPCOMING");
  const sale = running ?? next;

  if (!sale) {
    return null;
  }

  return (
    <>
      {running ? <SaleMarquee sale={running} /> : null}

      <section className="border-b border-rule px-6 py-14 sm:px-12">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label text-muted">{running ? "On now" : "Coming up"}</p>
            <h2 className="mt-2 font-display text-3xl uppercase tracking-[0.045em] sm:text-4xl">
              {sale.name}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-8">
            <SaleClock sale={sale} />
            <Link href="/sales" className="label text-muted underline underline-offset-4 hover:text-ink">
              All sales
            </Link>
          </div>
        </div>

        {sale.items.length > 0 ? (
          <div className="mt-10 grid grid-cols-2 gap-x-6 gap-y-12 lg:grid-cols-4">
            {sale.items.slice(0, 4).map((item) => (
              <SaleItemCard key={item.id} item={item} isRunning={Boolean(running)} />
            ))}
          </div>
        ) : null}
      </section>
    </>
  );
}
