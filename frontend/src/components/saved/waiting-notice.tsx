"use client";

import Link from "next/link";

import { useWaiting } from "@/hooks/use-saved";
import { opensWhen } from "@/lib/saved";

/** The one thing worth interrupting someone with on arrival.
 *
 * A sale they marked has opened. That is the whole reason the mark was made,
 * and it is the only state loud enough to earn a band across the page — an
 * upcoming sale is not urgent, so it says its time and nothing more. */
export function WaitingNotice() {
  const { data } = useWaiting();

  const open = data?.open_now;
  if (open) {
    return (
      <Link
        href="/sales"
        className="block bg-ink px-6 py-3 text-paper transition-colors hover:bg-ink-soft sm:px-12"
      >
        <span className="label flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="text-hold">Open now</span>
          <span>{open.sale_name}</span>
          {open.saved_in_sale > 0 ? (
            <span className="text-paper/70">
              {open.saved_in_sale} you kept {open.saved_in_sale === 1 ? "is" : "are"} in it
            </span>
          ) : null}
        </span>
      </Link>
    );
  }

  const next = data?.opening_next;
  if (next) {
    return (
      <Link
        href="/sales"
        className="block border-b border-rule px-6 py-2.5 transition-colors hover:bg-panel sm:px-12"
      >
        <span className="label flex flex-wrap items-center gap-x-4 gap-y-1 text-muted">
          <span className="text-ink">{next.sale_name}</span>
          <span className="tabular">{opensWhen(next.starts_at)}</span>
        </span>
      </Link>
    );
  }

  return null;
}
