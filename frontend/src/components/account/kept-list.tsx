"use client";

import Image from "next/image";
import Link from "next/link";

import { useForgetProduct, useReminders, useSaved } from "@/hooks/use-saved";
import { formatPrice } from "@/lib/catalogue";
import { discountPercent } from "@/lib/sales";
import { opensWhen, type Reminder, type SavedItem } from "@/lib/saved";

export function KeptList() {
  const { data: saved, isPending, isError } = useSaved();
  const { data: reminders } = useReminders();

  // What is on now leads, because it is the only part with a clock running.
  const onNow = saved?.filter((item) => item.sale_status === "ACTIVE") ?? [];
  const coming = saved?.filter((item) => item.sale_status === "UPCOMING") ?? [];
  const resting = saved?.filter((item) => item.sale_status === null) ?? [];
  const marked = reminders ?? [];

  return (
    <>
      <header>
        <p className="font-script text-2xl leading-none text-ink-soft">Yours to watch</p>
        <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Kept</h1>
        <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
          Things you have marked, and the sales you asked to be shown. Nothing here is held
          for you — a sale still has to be reached in time.
        </p>
      </header>

      {isError ? (
        <p className="mt-14 border-l-2 border-reject pl-4 text-sm text-reject">
          Your list could not be loaded. Try again in a moment.
        </p>
      ) : isPending ? (
        <p className="tabular mt-14 text-sm text-muted">Loading…</p>
      ) : saved.length === 0 && marked.length === 0 ? (
        <Nothing />
      ) : (
        <>
          {onNow.length > 0 ? (
            <Section title="On sale now" tone="urgent">
              {onNow.map((item) => (
                <KeptItem key={item.id} item={item} />
              ))}
            </Section>
          ) : null}

          {marked.length > 0 ? (
            <section className="mt-12 border-t border-rule pt-7">
              <h2 className="label text-muted">Sales on your list</h2>
              <ul className="mt-2">
                {marked.map((reminder) => (
                  <MarkedSale key={reminder.id} reminder={reminder} />
                ))}
              </ul>
            </section>
          ) : null}

          {coming.length > 0 ? (
            <Section title="In a sale coming up">
              {coming.map((item) => (
                <KeptItem key={item.id} item={item} />
              ))}
            </Section>
          ) : null}

          {resting.length > 0 ? (
            <Section title="Not in a sale">
              {resting.map((item) => (
                <KeptItem key={item.id} item={item} />
              ))}
            </Section>
          ) : null}
        </>
      )}
    </>
  );
}

function Section({
  title,
  tone,
  children,
}: {
  title: string;
  tone?: "urgent";
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12 border-t border-rule pt-7">
      <h2 className={`label ${tone === "urgent" ? "text-hold" : "text-muted"}`}>{title}</h2>
      <ul className="mt-2">{children}</ul>
    </section>
  );
}

function KeptItem({ item }: { item: SavedItem }) {
  const forget = useForgetProduct();
  const off =
    item.sale_price !== null ? discountPercent(item.normal_price, item.sale_price) : 0;
  const soldOut = item.available_quantity === 0;

  return (
    <li className="relative flex flex-wrap items-center gap-x-8 gap-y-4 border-b border-rule py-5 pl-5">
      {/* The mark itself, carried through from the card that was kept. */}
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-hold" />

      <Link href={`/products/${item.product_slug}`} className="shrink-0">
        <div className="relative h-16 w-16 overflow-hidden bg-panel">
          {item.image_url ? (
            <Image src={item.image_url} alt="" fill sizes="64px" className="object-contain p-2" />
          ) : null}
        </div>
      </Link>

      <div className="min-w-[10rem] flex-1">
        <Link
          href={`/products/${item.product_slug}`}
          className="text-sm leading-snug text-ink hover:underline hover:underline-offset-4"
        >
          {item.product_name}
        </Link>
        <p className="tabular mt-1.5 text-xs text-muted">
          {item.sale_price !== null ? (
            <>
              <span className="text-ink">{formatPrice(item.sale_price)}</span>{" "}
              <span className="line-through">{formatPrice(item.normal_price)}</span>
              {off > 0 ? <span className="text-hold"> · {off}% off</span> : null}
            </>
          ) : (
            formatPrice(item.normal_price)
          )}
        </p>
      </div>

      <div className="text-right">
        {item.sale_status === "ACTIVE" ? (
          <>
            <p className={`tabular text-sm ${soldOut ? "text-reject" : "text-hold"}`}>
              {soldOut ? "All gone" : `${item.available_quantity} left`}
            </p>
            {!soldOut ? (
              <Link
                href="/sales"
                className="label mt-1.5 inline-block text-muted underline underline-offset-4
                           transition-colors hover:text-ink"
              >
                Go and hold it
              </Link>
            ) : null}
          </>
        ) : item.sale_status === "UPCOMING" && item.starts_at ? (
          <>
            <p className="tabular text-sm text-ink">{opensWhen(item.starts_at)}</p>
            <p className="label mt-1.5 text-muted">{item.sale_name}</p>
          </>
        ) : (
          <button
            onClick={() => forget.mutate(item.product_id)}
            disabled={forget.isPending}
            className="label text-muted underline underline-offset-4 transition-colors
                       hover:text-reject disabled:opacity-40"
          >
            {forget.isPending ? "Removing" : "Remove"}
          </button>
        )}
      </div>
    </li>
  );
}

function MarkedSale({ reminder }: { reminder: Reminder }) {
  const running = reminder.status === "ACTIVE";

  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 border-b border-rule py-5">
      <div>
        <p className="text-sm text-ink">{reminder.sale_name}</p>
        <p className="label mt-1.5 text-muted">
          {reminder.item_count} {reminder.item_count === 1 ? "piece" : "pieces"}
          {reminder.saved_in_sale > 0
            ? ` · ${reminder.saved_in_sale} you kept`
            : ""}
        </p>
      </div>

      <div className="text-right">
        {running ? (
          <Link href="/sales" className="label text-hold underline underline-offset-4 hover:text-ink">
            On now — go
          </Link>
        ) : (
          <p className="tabular text-sm text-ink">{opensWhen(reminder.starts_at)}</p>
        )}
      </div>
    </li>
  );
}

function Nothing() {
  return (
    <div className="mt-14 border-t border-rule pt-8">
      <p className="font-display text-2xl text-ink">Nothing kept.</p>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
        Sales open for a few hours at a time. Mark what you want beforehand and it will be
        waiting here when the doors open.
      </p>
      <div className="mt-8 flex flex-wrap gap-4">
        <Link
          href="/products"
          className="label border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
        >
          Browse the shop
        </Link>
        <Link
          href="/sales"
          className="label border border-rule px-8 py-3.5 text-muted transition-colors
                     hover:border-ink hover:text-ink"
        >
          See what is coming
        </Link>
      </div>
    </div>
  );
}
