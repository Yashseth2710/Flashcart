"use client";

import Image from "next/image";
import Link from "next/link";

import { useOrders } from "@/hooks/use-orders";
import { useSession } from "@/hooks/use-session";
import { formatPrice } from "@/lib/catalogue";
import { type Order, type OrderLine, shortReference } from "@/lib/orders";

export function OrderList() {
  const { profile } = useSession();
  const { data, isPending, isError } = useOrders({ enabled: Boolean(profile) });

  return (
    <>
      <header>
        <p className="font-script text-2xl leading-none text-ink-soft">Yours for good</p>
        <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Orders</h1>
      </header>

      {isError ? (
        <p className="mt-14 border-l-2 border-reject pl-4 text-sm text-reject">
          Your orders could not be loaded. Try again in a moment.
        </p>
      ) : isPending ? (
        <p className="tabular mt-14 text-sm text-muted">Loading…</p>
      ) : data.length === 0 ? (
        <Nothing />
      ) : (
        <div className="mt-14 border-t border-rule">
          {data.map((order) => (
            <OrderBlock key={order.id} order={order} />
          ))}
        </div>
      )}
    </>
  );
}

function OrderBlock({ order }: { order: Order }) {
  const placed = new Date(order.placed_at);

  return (
    <section className="border-b border-rule py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
        <div>
          {/* The reference is what someone quotes when asking about an order,
              so it reads first and in the face made for numbers. */}
          <p className="tabular text-sm text-ink">{shortReference(order.id)}</p>
          <p className="label mt-1.5 text-muted">
            {placed.toLocaleDateString(undefined, {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
            {order.sale_name ? ` · ${order.sale_name}` : ""}
          </p>
        </div>

        <div className="text-right">
          <p className="tabular text-sm text-ink">{formatPrice(order.total)}</p>
          <p className={`label mt-1.5 ${order.status === "CANCELLED" ? "text-reject" : "text-fill"}`}>
            {wordFor(order.status)}
          </p>
        </div>
      </div>

      <ul className="mt-6">
        {order.items.map((line) => (
          <Line key={line.id} line={line} />
        ))}
      </ul>
    </section>
  );
}

function Line({ line }: { line: OrderLine }) {
  const name = (
    <>
      <p className="text-sm leading-snug text-ink">{line.product_name}</p>
      <p className="tabular mt-1.5 text-xs text-muted">
        {line.quantity} × {formatPrice(line.price)}
      </p>
    </>
  );

  return (
    <li className="flex items-center gap-6 py-3">
      <div className="relative h-14 w-14 shrink-0 overflow-hidden bg-panel">
        {line.image_url ? (
          <Image src={line.image_url} alt="" fill sizes="56px" className="object-contain p-2" />
        ) : null}
      </div>

      {/* A product taken out of the catalogue has nowhere to link to, but the
          line still has to read correctly. */}
      <div className="min-w-0 flex-1">
        {line.product_slug ? (
          <Link href={`/products/${line.product_slug}`} className="block hover:underline hover:underline-offset-4">
            {name}
          </Link>
        ) : (
          name
        )}
      </div>

      <p className="tabular text-sm text-ink-soft">{formatPrice(line.line_total)}</p>
    </li>
  );
}

function wordFor(status: Order["status"]): string {
  if (status === "PAID") return "Paid";
  if (status === "FULFILLED") return "Sent";
  return "Cancelled";
}

function Nothing() {
  return (
    <div className="mt-14 border-t border-rule pt-8">
      <p className="font-display text-2xl text-ink">Nothing bought yet.</p>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-soft">
        Hold something in a running sale, then buy it before the clock runs out.
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
