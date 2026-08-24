"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { holdsKey } from "@/hooks/use-holds";
import { ApiError } from "@/lib/api";
import { checkOut, fetchOrders } from "@/lib/orders";

export const ordersKey = ["orders"] as const;

export function useOrders({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ordersKey,
    queryFn: fetchOrders,
    enabled,
    // Not being signed in is an answer, not a failure worth retrying.
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 1,
  });
}

export function useCheckout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: checkOut,
    // A purchase moves a hold, the stock behind it, and the order list, so all
    // three are re-read. Retries are safe: the key makes them settle as one.
    retry: (count, error) => {
      const status = error instanceof ApiError ? error.status : 0;
      // Declines and refusals are answers. Only a broken connection is worth
      // trying again, and the idempotency key is what makes that safe.
      return status === 0 && count < 2;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ordersKey });
      void queryClient.invalidateQueries({ queryKey: holdsKey });
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
    },
  });
}
