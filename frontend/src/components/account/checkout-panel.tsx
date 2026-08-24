"use client";

import { useRef, useState } from "react";

import { useCheckout } from "@/hooks/use-orders";
import { ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/catalogue";
import type { Hold } from "@/lib/holds";
import { keyForCheckout } from "@/lib/orders";

/** Paying for one hold.
 *
 * The clock is still running while this is open, so the panel stays inside the
 * row it belongs to rather than covering the page: what they are about to lose
 * remains in view the whole time. */
export function CheckoutPanel({
  hold,
  onDone,
  onBought,
}: {
  hold: Hold;
  onDone: () => void;
  onBought: (orderId: string) => void;
}) {
  const checkout = useCheckout();
  const [card, setCard] = useState("4242 4242 4242 4242");

  // Held still for the life of this panel, so every retry of this purchase
  // carries the same key and settles as one order.
  const key = useRef(keyForCheckout(hold.id));

  return (
    <div className="mt-6 border-l-2 border-hold pl-5">
      <p className="label text-muted">Paying</p>

      <dl className="mt-4 max-w-xs">
        <Row term={`${hold.product_name} × ${hold.quantity}`} value={formatPrice(hold.line_total)} />
        <Row term="To pay" value={formatPrice(hold.line_total)} strong />
      </dl>

      <label className="mt-6 block">
        {/* Block, or the span stays inline and the field rides up beside it. */}
        <span className="label block text-muted">Card number</span>
        <input
          value={card}
          onChange={(event) => setCard(event.target.value)}
          inputMode="numeric"
          autoComplete="cc-number"
          className="tabular mt-2 w-full max-w-xs border-b border-rule bg-transparent pb-2 text-sm
                     outline-none transition-colors focus:border-ink"
        />
      </label>
      <p className="mt-2 text-xs leading-relaxed text-muted">
        No real card is charged. Ending 0002 is declined, anything else is taken.
      </p>

      {checkout.error ? (
        <p role="alert" className="mt-5 max-w-xs text-sm leading-relaxed text-reject">
          {checkout.error instanceof ApiError ? checkout.error.message : "Could not pay."}
        </p>
      ) : null}

      <div className="mt-7 flex flex-wrap items-center gap-6">
        <button
          onClick={() =>
            checkout.mutate(
              {
                reservation_id: hold.id,
                idempotency_key: key.current,
                card_number: card.replace(/\s/g, ""),
              },
              { onSuccess: (order) => onBought(order.id) },
            )
          }
          disabled={checkout.isPending}
          className="label border border-ink px-8 py-3.5 transition-colors
                     hover:bg-ink hover:text-paper disabled:opacity-40"
        >
          {checkout.isPending ? "Paying" : `Pay ${formatPrice(hold.line_total)}`}
        </button>
        <button onClick={onDone} className="label text-muted hover:text-ink">
          Not now
        </button>
      </div>
    </div>
  );
}

function Row({ term, value, strong }: { term: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-rule py-2.5">
      <dt className={`text-xs ${strong ? "text-ink" : "text-muted"}`}>{term}</dt>
      <dd className={`tabular text-sm ${strong ? "text-ink" : "text-ink-soft"}`}>{value}</dd>
    </div>
  );
}
