"use client";

import Link from "next/link";

import { LogoInline } from "@/components/brand/logo";
import { useLogout, useSession } from "@/hooks/use-session";

export function SiteHeader() {
  const { profile, isLoading } = useSession();
  const { mutate: signOut, isPending } = useLogout();

  return (
    <header className="flex items-baseline justify-between border-b border-rule px-6 py-6 sm:px-12">
      <Link href="/" aria-label="FlashCart home">
        <LogoInline />
      </Link>

      <nav className="label flex items-center gap-7 text-muted">
        {isLoading ? null : profile ? (
          <>
            {profile.role === "ADMIN" ? (
              <Link href="/admin" className="hover:text-ink">
                Admin
              </Link>
            ) : null}
            <span className="hidden text-ink sm:inline">{profile.name}</span>
            <button onClick={() => signOut()} disabled={isPending} className="hover:text-ink">
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="hover:text-ink">
              Sign in
            </Link>
            <Link href="/register" className="hover:text-ink">
              Create account
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
