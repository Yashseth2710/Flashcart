"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api";
import type { Profile } from "@/lib/session";
import { fetchProfile, login, logout, register } from "@/lib/session";

const sessionKey = ["session"] as const;

export function useSession() {
  const { data, isPending } = useQuery({
    queryKey: sessionKey,
    queryFn: async () => {
      try {
        return await fetchProfile();
      } catch (error) {
        // Not being signed in is an answer, so it is returned rather than
        // thrown. A thrown one is an error as far as the cache is concerned,
        // and an errored query is asked again the moment another component
        // subscribes to it — which on pages whose signed-in parts appear only
        // once their own data has arrived meant asking the server a second
        // time to be told the same thing.
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    retry: 1,
    staleTime: 5 * 60_000,
  });

  return { profile: data ?? null, isLoading: isPending };
}

function useSessionStart<T>(action: (values: T) => Promise<Profile>, destination: string) {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: action,
    onSuccess: (profile) => {
      queryClient.setQueryData(sessionKey, profile);
      router.push(destination);
      router.refresh();
    },
  });
}

export function useLogin(destination = "/") {
  return useSessionStart(login, destination);
}

export function useRegister(destination = "/") {
  return useSessionStart(register, destination);
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(sessionKey, null);
      queryClient.clear();
      router.push("/");
      router.refresh();
    },
  });
}
