"use client";

import { formatRemaining, useCountdown } from "@/hooks/use-countdown";
import type { SaleDetail } from "@/lib/sales";

/** Repeats per half. Six copies of a short phrase cross a wide screen, and the
 *  cost of a few extra is a handful of spans nobody will ever count. */
const REPEATS = 6;

/** The one loud thing on a quiet page: a live sale, scrolling, with its clock. */
export function SaleMarquee({ sale }: { sale: SaleDetail }) {
  const isRunning = sale.status === "ACTIVE";
  const remaining = useCountdown(isRunning ? sale.end_time : sale.start_time);
  const label = isRunning ? "Ends in" : "Starts in";

  const phrase = `${sale.name} · ${label} ${formatRemaining(remaining)}`;

  return (
    <div className="overflow-hidden border-y border-ink bg-ink py-3 text-paper">
      {/* Two halves, each holding the same run of phrases. The animation moves
          by exactly one half, so at the end of a cycle the second half is
          sitting where the first began and the jump back cannot be seen.

          Each half repeats the phrase enough times to cross the widest screen
          on its own, which is what keeps the line unbroken: a short sale name
          would otherwise run out mid-page and leave the rest of the strip bare. */}
      <div className="flex w-max animate-marquee whitespace-nowrap will-change-transform">
        {[0, 1].map((half) => (
          <span key={half} className="flex" aria-hidden={half === 1 ? "true" : undefined}>
            {Array.from({ length: REPEATS }, (_, index) => (
              <span
                key={index}
                className="label tabular flex items-center gap-10 pr-10 text-paper"
                /* Said once. The repeats are the same words over again. */
                aria-hidden={index > 0 ? "true" : undefined}
              >
                {phrase}
                <span aria-hidden="true">✳</span>
              </span>
            ))}
          </span>
        ))}
      </div>
    </div>
  );
}
