"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/hooks/use-session";

/** Hiding the screen is presentation, not protection; the service checks the
 *  role on every request regardless of what the browser shows. */
export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { profile, isLoading } = useSession();
  const router = useRouter();
  const allowed = profile?.role === "ADMIN";

  useEffect(() => {
    if (!isLoading && !allowed) {
      router.replace(profile ? "/" : "/login");
    }
  }, [isLoading, allowed, profile, router]);

  if (isLoading) {
    return <p className="tabular px-6 py-20 text-sm text-muted sm:px-12">Checking…</p>;
  }

  return allowed ? <>{children}</> : null;
}
