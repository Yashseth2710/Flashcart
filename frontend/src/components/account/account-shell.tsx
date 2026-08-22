"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/hooks/use-session";

/** Sections of the account area. Holds and orders arrive with the parts of the
 *  shop that create them. */
const sections = [{ href: "/account/settings", label: "Settings" }] as const;

export function AccountShell({ children }: { children: React.ReactNode }) {
  const { profile, isLoading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !profile) {
      router.replace("/login");
    }
  }, [isLoading, profile, router]);

  if (isLoading) {
    return <p className="tabular px-6 py-20 text-sm text-muted sm:px-12">Loading…</p>;
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="px-6 pb-24 sm:px-12 lg:grid lg:grid-cols-[13rem_1fr] lg:gap-16">
      <nav aria-label="Your account" className="border-b border-rule py-8 lg:border-b-0 lg:py-12">
        <p className="label text-muted">Your account</p>
        <p className="mt-2 font-display text-xl">{profile.name}</p>

        <ul className="mt-8 flex gap-6 lg:mt-10 lg:flex-col lg:gap-0">
          {sections.map((section) => {
            const isHere = pathname === section.href;
            return (
              <li key={section.href} className="lg:border-t lg:border-rule">
                <Link
                  href={section.href}
                  aria-current={isHere ? "page" : undefined}
                  className={`label block transition-colors lg:py-3.5 ${
                    isHere ? "text-ink" : "text-muted hover:text-ink"
                  }`}
                >
                  {section.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <main className="py-10 lg:py-12">{children}</main>
    </div>
  );
}
