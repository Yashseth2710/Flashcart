"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useSession } from "@/hooks/use-session";
import { ApiError } from "@/lib/api";
import {
  fetchReminders,
  fetchSaved,
  fetchWaiting,
  forgetProduct,
  forgetSale,
  remindMe,
  saveProduct,
} from "@/lib/saved";

export const savedKey = ["saved"] as const;
export const remindersKey = ["reminders"] as const;
export const waitingKey = ["waiting"] as const;

/** Not being signed in is an answer, not a failure worth retrying. */
const dontRetryUnauthorised = (count: number, error: unknown) =>
  !(error instanceof ApiError && error.status === 401) && count < 1;

export function useSaved() {
  const { profile } = useSession();
  return useQuery({
    queryKey: savedKey,
    queryFn: fetchSaved,
    enabled: Boolean(profile),
    retry: dontRetryUnauthorised,
  });
}

export function useReminders() {
  const { profile } = useSession();
  return useQuery({
    queryKey: remindersKey,
    queryFn: fetchReminders,
    enabled: Boolean(profile),
    retry: dontRetryUnauthorised,
  });
}

/** The small summary the header reads on every page.
 *
 * Re-checked on a timer because a sale someone marked can open while they are
 * sitting on a page, and that is the one moment worth interrupting for. */
export function useWaiting() {
  const { profile } = useSession();
  return useQuery({
    queryKey: waitingKey,
    queryFn: fetchWaiting,
    enabled: Boolean(profile),
    retry: dontRetryUnauthorised,
    refetchInterval: 60_000,
  });
}

function useAfterMarking() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: savedKey });
    void queryClient.invalidateQueries({ queryKey: remindersKey });
    void queryClient.invalidateQueries({ queryKey: waitingKey });
  };
}

export function useSaveProduct() {
  const refresh = useAfterMarking();
  return useMutation({ mutationFn: saveProduct, onSuccess: refresh });
}

export function useForgetProduct() {
  const refresh = useAfterMarking();
  // Refreshed even on failure: "not saved" means the list already moved.
  return useMutation({ mutationFn: forgetProduct, onSettled: refresh });
}

export function useRemindMe() {
  const refresh = useAfterMarking();
  return useMutation({ mutationFn: remindMe, onSuccess: refresh });
}

export function useForgetSale() {
  const refresh = useAfterMarking();
  return useMutation({ mutationFn: forgetSale, onSettled: refresh });
}
