"use client";

import Link from "next/link";
import { useState } from "react";

import { usePlaceHold } from "@/hooks/use-holds";
import { useSession } from "@/hooks/use-session";
import { ApiError } from "@/lib/api";
import type { SaleItem } from "@/lib/sales";

/** Taking stock off the shelf, from the card it sits on.
 *
 * Only ever shown on a sale that is running. Before one starts there is nothing
 * to take, and after it ends there is nothing to take it from. */
export function ReserveControl({ item }: { item: SaleItem }) {
  const { profile, isLoading } = useSession();
  const place = usePlaceHold();
  const [quantity, setQuantity] = useState(1);
  const [justHeld, setJustHeld] = useState(0);

  const soldOut = item.available_quantity === 0;
  const ceiling = Math.min(item.max_per_user, item.available_quantity);

  // What was held is remembered here rather than read from the mutation, whose
  // success state is wiped when the refreshed numbers re-render this card.
  // Sold out is still worth confirming, since it is what they just did.
  if (justHeld > 0) {
    return (
      <p className="pt-[3.6rem] text-xs leading-relaxed text-fill">
        {justHeld} held.{" "}
        <Link href="/account/holds" className="underline underline-offset-4 hover:text-ink">
          Go to your holds
        </Link>
      </p>
    );
  }

  if (soldOut) {
    return <p className="label pt-[3.6rem] text-muted">All gone</p>;
  }

  if (isLoading) {
    return <p className="label py-3.5 text-muted">&nbsp;</p>;
  }

  if (!profile) {
    return (
      <Link
        href="/login"
        className="label block border border-rule py-3.5 text-center text-muted
                   transition-colors hover:border-ink hover:text-ink"
      >
        Sign in to hold
      </Link>
    );
  }

  // Stock can fall while the stepper is sitting on a number, so what is asked
  // for is bounded by what is actually there at the moment of asking.
  const wanted = Math.min(quantity, Math.max(1, ceiling));

  return (
    <div>
      {/* A one-per-person item has no stepper, but still leaves room for one,
          so every button in a row sits on the same line. */}
      {ceiling > 1 ? (
        <Stepper value={wanted} ceiling={ceiling} onChange={setQuantity} />
      ) : (
        <div aria-hidden="true" className="h-[2.6875rem]" />
      )}

      <button
        onClick={() =>
          place.mutate(
            { sale_product_id: item.id, quantity: wanted },
            { onSuccess: (hold) => setJustHeld(hold.quantity) },
          )
        }
        disabled={place.isPending}
        className="label mt-2 w-full border border-ink py-3.5 transition-colors
                   hover:bg-ink hover:text-paper disabled:opacity-40"
      >
        {place.isPending ? "Holding" : "Hold it"}
      </button>

      {place.error ? (
        <p role="alert" className="mt-3 text-xs leading-relaxed text-reject">
          {place.error instanceof ApiError ? place.error.message : "Could not hold it."}
        </p>
      ) : null}
    </div>
  );
}

/** How many, when more than one is allowed. Bounded by the per-person limit
 *  and by what is actually left, whichever runs out first. */
function Stepper({
  value,
  ceiling,
  onChange,
}: {
  value: number;
  ceiling: number;
  onChange: (next: number) => void;
}) {
  const step = (by: number) => onChange(Math.min(ceiling, Math.max(1, value + by)));

  return (
    <div className="flex items-center justify-between border border-rule">
      <StepButton label="One fewer" onClick={() => step(-1)} disabled={value <= 1}>
        –
      </StepButton>
      <span className="tabular text-xs text-ink" aria-live="polite">
        {value}
      </span>
      <StepButton label="One more" onClick={() => step(1)} disabled={value >= ceiling}>
        +
      </StepButton>
    </div>
  );
}

function StepButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="px-4 py-2.5 text-sm text-muted transition-colors hover:text-ink
                 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:text-muted"
    >
      {children}
    </button>
  );
}
