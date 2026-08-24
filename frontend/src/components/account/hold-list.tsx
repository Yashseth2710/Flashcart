"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useHolds, useReleaseHold } from "@/hooks/use-holds";
import { ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/catalogue";
import { formatRemaining, type Hold } from "@/lib/holds";
import { useSession } from "@/hooks/use-session";

export function HoldList() {
  const { profile } = useSession();
  const { data, isPending, isError } = useHolds({ enabled: Boolean(profile) });

  const live = data?.filter((hold) => hold.status === "ACTIVE") ?? [];
  const past = data?.filter((hold) => hold.status !== "ACTIVE") ?? [];

  return (
    <>
      <header>
        <p className="font-script text-2xl leading-none text-ink-soft">Yours for now</p>
        <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Holds</h1>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
          Stock in a flash sale is held for a few minutes at a time. When the clock runs out it
          goes back to the sale for someone else.
        </p>
      </header>

      {isError ? (
        <p className="mt-14 border-l-2 border-reject pl-4 text-sm text-reject">
          Your holds could not be loaded. Try again in a moment.
        </p>
      ) : isPending ? (
        <p className="tabular mt-14 text-sm text-muted">Loading…</p>
      ) : live.length === 0 && past.length === 0 ? (
        <Nothing />
      ) : (
        <>
          {live.length > 0 ? (
            <section className="mt-14 border-t border-rule pt-8">
              <h2 className="label text-muted">Counting down</h2>
              <ul>
                {live.map((hold) => (
                  <LiveHold key={hold.id} hold={hold} />
                ))}
              </ul>
            </section>
          ) : null}

          {past.length > 0 ? (
            <section className="mt-14 border-t border-rule pt-8">
              <h2 className="label text-muted">Finished</h2>
              <ul>
                {past.map((hold) => (
                  <PastHold key={hold.id} hold={hold} />
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </>
  );
}

/** A hold with time left. The clock is the point of the row, so it is the
 *  largest thing in it and the only thing that moves. */
function LiveHold({ hold }: { hold: Hold }) {
  const remaining = useTicker(hold.expires_at);
  const release = useReleaseHold();

  // The last minute is when it starts to matter, so that is when it changes colour.
  const urgent = remaining <= 60;
  const gone = remaining <= 0;

  return (
    <li className="flex flex-wrap items-center gap-x-8 gap-y-5 border-b border-rule py-6">
      <Thumbnail hold={hold} />

      <div className="min-w-[10rem] flex-1">
        <Link
          href={`/products/${hold.product_slug}`}
          className="text-sm leading-snug text-ink hover:underline hover:underline-offset-4"
        >
          {hold.product_name}
        </Link>
        <p className="tabular mt-1.5 text-xs text-muted">
          {hold.quantity} × {formatPrice(hold.sale_price)} · {hold.sale_name}
        </p>
      </div>

      <div className="text-right">
        <p
          className={`tabular text-2xl leading-none tracking-tight ${
            gone ? "text-muted" : urgent ? "text-reject" : "text-hold"
          }`}
          // Read out only as it becomes urgent, rather than every second.
          aria-live={urgent ? "polite" : "off"}
        >
          {gone ? "—" : formatRemaining(remaining)}
        </p>
        <p className="label mt-2 text-muted">{gone ? "Time up" : "left"}</p>
      </div>

      <div className="text-right">
        <p className="tabular text-sm text-ink">{formatPrice(hold.line_total)}</p>
        <button
          onClick={() => release.mutate(hold.id)}
          disabled={release.isPending}
          className="label mt-2 text-muted underline underline-offset-4 transition-colors
                     hover:text-reject disabled:opacity-40"
        >
          {release.isPending ? "Letting go" : "Let it go"}
        </button>
        {release.error ? (
          <p role="alert" className="mt-2 max-w-[12rem] text-xs leading-relaxed text-reject">
            {release.error instanceof ApiError ? release.error.message : "Could not let it go."}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function PastHold({ hold }: { hold: Hold }) {
  const wording = {
    EXPIRED: "Ran out of time",
    CANCELLED: "Let go",
    COMPLETED: "Bought",
    ACTIVE: "",
  } as const;

  return (
    <li className="flex flex-wrap items-center gap-x-8 gap-y-4 border-b border-rule py-5 opacity-60">
      <Thumbnail hold={hold} />

      <div className="min-w-[10rem] flex-1">
        <Link
          href={`/products/${hold.product_slug}`}
          className="text-sm leading-snug text-ink hover:underline hover:underline-offset-4"
        >
          {hold.product_name}
        </Link>
        <p className="tabular mt-1.5 text-xs text-muted">
          {hold.quantity} × {formatPrice(hold.sale_price)} · {hold.sale_name}
        </p>
      </div>

      <p className="label text-muted">{wording[hold.status]}</p>
    </li>
  );
}

function Thumbnail({ hold }: { hold: Hold }) {
  return (
    <div className="relative h-16 w-16 shrink-0 overflow-hidden bg-panel">
      {hold.image_url ? (
        <Image src={hold.image_url} alt="" fill sizes="64px" className="object-contain p-2" />
      ) : null}
    </div>
  );
}

function Nothing() {
  return (
    <div className="mt-14 border-t border-rule pt-8">
      <p className="font-display text-2xl text-ink">Nothing held.</p>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
        When a sale is running you can hold what you want while you decide.
      </p>
      <Link
        href="/sales"
        className="label mt-8 inline-block border border-ink px-8 py-3.5 transition-colors
                   hover:bg-ink hover:text-paper"
      >
        See what is on
      </Link>
    </div>
  );
}

const secondsUntil = (deadline: number) => Math.max(0, Math.round((deadline - Date.now()) / 1000));

/** Counts down locally so the clock moves every second without asking the
 *  server every second. The deadline is the truth rather than a running total,
 *  so a tab that was asleep catches up instead of drifting. */
function useTicker(expiresAt: string): number {
  const deadline = new Date(expiresAt).getTime();
  const [remaining, setRemaining] = useState(() => secondsUntil(deadline));
  const [countingTo, setCountingTo] = useState(deadline);

  // A different deadline resets during render rather than after it, which
  // avoids a frame showing the previous hold's time.
  if (countingTo !== deadline) {
    setCountingTo(deadline);
    setRemaining(secondsUntil(deadline));
  }

  useEffect(() => {
    if (secondsUntil(deadline) <= 0) return;

    const timer = setInterval(() => {
      const next = secondsUntil(deadline);
      setRemaining(next);
      if (next <= 0) clearInterval(timer);
    }, 1000);

    return () => clearInterval(timer);
  }, [deadline]);

  return remaining;
}
