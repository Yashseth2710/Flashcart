"use client";

import { formatRemaining, useCountdown } from "@/hooks/use-countdown";
import type { SaleDetail } from "@/lib/sales";

/** Whichever moment matters next: the opening, or the closing. */
export function SaleClock({ sale }: { sale: SaleDetail }) {
  const isRunning = sale.status === "ACTIVE";
  const remaining = useCountdown(isRunning ? sale.end_time : sale.start_time);

  if (sale.status === "ENDED") {
    return <p className="label text-muted">This sale is over</p>;
  }

  return (
    <div className="flex items-baseline gap-4">
      <span className="label text-muted">{isRunning ? "Ends in" : "Opens in"}</span>
      <span className={`tabular text-2xl ${isRunning ? "text-hold" : "text-ink"}`}>
        {formatRemaining(remaining)}
      </span>
    </div>
  );
}
