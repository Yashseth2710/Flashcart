"use client";

import Link from "next/link";

import { LogoInline } from "@/components/brand/logo";
import { useLogout, useSession } from "@/hooks/use-session";

export function SiteHeader() {
  const { profile, isLoading } = useSession();
  const { mutate: signOut, isPending } = useLogout();

  return (
    <header className="border-b border-rule px-6 py-5 sm:px-12 sm:py-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-3">
        <Link href="/" aria-label="FlashCart home" className="shrink-0">
          <LogoInline />
        </Link>

        <nav className="label flex flex-wrap items-baseline gap-x-6 gap-y-2 text-muted">
          <Link href="/sales" className="hover:text-ink">
            Sales
          </Link>
          <Link href="/products" className="hover:text-ink">
            Shop
          </Link>

          {isLoading ? null : profile ? (
            <>
              {profile.role === "ADMIN" ? (
                <Link href="/admin/sales" className="hover:text-ink">
                  Admin
                </Link>
              ) : null}
              <span className="hidden text-ink md:inline">{profile.name}</span>
              <button
                onClick={() => signOut()}
                disabled={isPending}
                className="whitespace-nowrap hover:text-ink"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:text-ink">
                Sign in
              </Link>
              <Link href="/register" className="whitespace-nowrap hover:text-ink">
                Create account
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
