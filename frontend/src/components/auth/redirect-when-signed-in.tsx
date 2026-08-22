"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/hooks/use-session";

/** Someone already signed in has no use for these pages. */
export function RedirectWhenSignedIn({ to = "/" }: { to?: string }) {
  const { profile } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (profile) {
      router.replace(to);
    }
  }, [profile, router, to]);

  return null;
}
