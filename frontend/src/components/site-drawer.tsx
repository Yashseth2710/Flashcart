"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import { useLogout, useSession } from "@/hooks/use-session";

type Props = {
  isOpen: boolean;
  onClose: () => void;
};

export function SiteDrawer({ isOpen, onClose }: Props) {
  const { profile } = useSession();
  const { mutate: signOut, isPending } = useLogout();
  const pathname = usePathname();
  const panel = useRef<HTMLDivElement>(null);

  // Escape closes it, and the page underneath stops scrolling while it is open.
  useEffect(() => {
    if (!isOpen) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);

    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [isOpen, onClose]);

  // Going somewhere closes it, so it is never left hanging over the new page.
  useEffect(() => {
    onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden="true"
        className={`fixed inset-0 z-40 bg-ink/25 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <div
        ref={panel}
        role="dialog"
        aria-label="Menu"
        aria-modal="true"
        tabIndex={-1}
        className={`fixed inset-y-0 left-0 z-50 flex w-[17rem] flex-col border-r border-rule
                    bg-paper px-8 py-7 outline-none transition-transform duration-300 ease-out ${
                      isOpen ? "translate-x-0" : "-translate-x-full"
                    }`}
      >
        <div className="flex items-baseline justify-between">
          <p className="label text-muted">Menu</p>
          <button onClick={onClose} aria-label="Close the menu" className="label text-muted hover:text-ink">
            Close
          </button>
        </div>

        <nav className="mt-9">
          <p className="text-[0.6rem] uppercase tracking-[0.24em] text-muted/70">Browse</p>
          <Group>
            <Item href="/sales" current={pathname}>
              Sales
            </Item>
            <Item href="/products" current={pathname}>
              Shop
            </Item>
          </Group>

          {profile ? (
            <>
              <p className="mt-9 text-[0.6rem] uppercase tracking-[0.24em] text-muted/70">{profile.name}</p>
              <Group>
                <Item href="/account/kept" current={pathname}>
                  Kept
                </Item>
                <Item href="/account/holds" current={pathname}>
                  Holds
                </Item>
                <Item href="/account/orders" current={pathname}>
                  Orders
                </Item>
                <Item href="/account/settings" current={pathname}>
                  Settings
                </Item>
                {profile.role === "ADMIN" ? (
                  <>
                    <Item href="/admin/sales" current={pathname}>
                      Manage sales
                    </Item>
                    <Item href="/admin" current={pathname}>
                      Manage catalogue
                    </Item>
                  </>
                ) : null}
              </Group>
            </>
          ) : (
            <>
              <p className="mt-9 text-[0.6rem] uppercase tracking-[0.24em] text-muted/70">Your account</p>
              <Group>
                <Item href="/login" current={pathname}>
                  Sign in
                </Item>
                <Item href="/register" current={pathname}>
                  Create an account
                </Item>
              </Group>
            </>
          )}

          {profile ? (
            <button
              onClick={() => signOut()}
              disabled={isPending}
              className="label w-full border-t border-rule py-3.5 text-left text-muted transition-colors hover:text-ink"
            >
              {isPending ? "Signing out" : "Sign out"}
            </button>
          ) : null}
        </nav>
      </div>
    </>
  );
}

function Group({ children }: { children: React.ReactNode }) {
  return <ul className="mt-4">{children}</ul>;
}

function Item({
  href,
  current,
  children,
}: {
  href: string;
  current: string;
  children: React.ReactNode;
}) {
  const isHere = current === href;
  return (
    <li className="border-t border-rule">
      <Link
        href={href}
        aria-current={isHere ? "page" : undefined}
        className={`label block py-3.5 transition-colors ${
          isHere ? "text-ink" : "text-muted hover:text-ink"
        }`}
      >
        {children}
      </Link>
    </li>
  );
}
