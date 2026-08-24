"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/lib/api";
import { fetchHolds, placeHold, releaseHold } from "@/lib/holds";

export const holdsKey = ["holds"] as const;

export function useHolds({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: holdsKey,
    queryFn: fetchHolds,
    enabled,
    // Not being signed in is an answer, not a failure worth retrying.
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 1,
    // A hold running out is worth noticing without a reload. The countdown
    // itself ticks locally; this only re-checks what the server thinks.
    refetchInterval: 30_000,
  });
}

/** Both counts move when a hold is placed or let go, so both are re-read. */
function useAfterHoldChanges() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: holdsKey });
    void queryClient.invalidateQueries({ queryKey: ["sales"] });
    void queryClient.invalidateQueries({ queryKey: ["sale"] });
  };
}

export function usePlaceHold() {
  const refresh = useAfterHoldChanges();
  return useMutation({ mutationFn: placeHold, onSuccess: refresh });
}

export function useReleaseHold() {
  const refresh = useAfterHoldChanges();
  // Refreshed even on failure: "already expired" means the numbers just moved.
  return useMutation({ mutationFn: releaseHold, onSettled: refresh });
}
