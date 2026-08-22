"use client";

import { formatRemaining, useCountdown } from "@/hooks/use-countdown";
import type { SaleDetail } from "@/lib/sales";

/** The one loud thing on a quiet page: a live sale, scrolling, with its clock. */
export function SaleMarquee({ sale }: { sale: SaleDetail }) {
  const isRunning = sale.status === "ACTIVE";
  const remaining = useCountdown(isRunning ? sale.end_time : sale.start_time);
  const label = isRunning ? "Ends in" : "Starts in";

  const phrase = `${sale.name} · ${label} ${formatRemaining(remaining)}`;

  return (
    <div className="overflow-hidden border-y border-ink bg-ink py-3 text-paper">
      <div className="flex w-max animate-marquee gap-10 whitespace-nowrap will-change-transform">
        {Array.from({ length: 4 }, (_, index) => (
          <span key={index} className="label tabular flex items-center gap-10 text-paper">
            {phrase}
            <span aria-hidden="true">✳</span>
          </span>
        ))}
      </div>
    </div>
  );
}
