"use client";

import Link from "next/link";
import { useState } from "react";

import { LogoInline } from "@/components/brand/logo";
import { SiteDrawer } from "@/components/site-drawer";
import { useSession } from "@/hooks/use-session";

export function SiteHeader() {
  const { profile, isLoading } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <header className="border-b border-rule px-6 py-5 sm:px-12 sm:py-6">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
          <div className="flex items-center gap-5">
            {/* The same warm gold as the cart mark beside it, so the two read as
                one pair. Two-pixel rules rather than hairlines: at 1px the browser
                has to blend a line across a pixel boundary and the three stop
                matching each other. */}
            <button
              onClick={() => setMenuOpen(true)}
              aria-label="Open the menu"
              aria-expanded={menuOpen}
              className="group -ml-1 flex h-7 w-8 shrink-0 items-center justify-center px-1"
            >
              <svg
                width="18"
                height="12"
                viewBox="0 0 18 12"
                aria-hidden="true"
                shapeRendering="crispEdges"
                className="text-hold transition-colors duration-200 group-hover:text-ink"
              >
                <rect y="0" width="18" height="2" fill="currentColor" />
                <rect y="5" width="18" height="2" fill="currentColor" />
                <rect y="10" width="18" height="2" fill="currentColor" />
              </svg>
            </button>

            <Link href="/" aria-label="FlashCart home" className="shrink-0">
              <LogoInline />
            </Link>
          </div>

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
                {/* Signing out lives in the menu and in settings, beside the
                    other things you do to your own account. */}
                <Link href="/account/settings" className="text-ink hover:text-ink-soft">
                  {profile.name.split(" ")[0]}
                </Link>
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

      <SiteDrawer isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
    </>
  );
}
