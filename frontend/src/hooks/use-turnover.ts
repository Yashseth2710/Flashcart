"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import type { SaleDetail } from "@/lib/sales";

/** Asks the server again at the exact moment a sale opens or closes.
 *
 *  Polling on its own is a compromise: too slow and the page keeps offering
 *  holds on a sale that has just shut, too fast and every idle browser is
 *  hammering the shop for news that has not happened yet.
 *
 *  The moment itself is already known — it is the sale's own start or end
 *  time — so it need not be discovered by asking repeatedly. This waits for
 *  that one second and asks then. The poll stays as the safety net for
 *  everything a clock cannot predict, which is mostly stock going.
 */
export function useTurnover(sale: SaleDetail | undefined) {
  const queryClient = useQueryClient();

  const turnsOverAt = sale
    ? new Date(sale.status === "ACTIVE" ? sale.end_time : sale.start_time).getTime()
    : null;

  useEffect(() => {
    if (turnsOverAt === null) return;

    const wait = turnsOverAt - Date.now();
    // Already past, or too far off to be worth holding a timer for: the poll
    // covers it. setTimeout also cannot be trusted beyond about 24 days.
    if (wait <= 0 || wait > 6 * 60 * 60_000) return;

    // A second's grace, so the server has certainly crossed the same boundary.
    // Asking a moment early would return the old status and settle nothing.
    const timer = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
    }, wait + 1000);

    return () => clearTimeout(timer);
  }, [turnsOverAt, queryClient]);
}
