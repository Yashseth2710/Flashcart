"use client";

import Link from "next/link";

import { useForgetProduct, useSaved, useSaveProduct } from "@/hooks/use-saved";
import { useSession } from "@/hooks/use-session";

/** Marking a product to come back to.
 *
 * A catalogue page gets marked, not hearted, so the control is a word and a
 * rule rather than an icon floating over the picture. "Keep" because that is
 * what a person does with a page they mean to return to. */
export function KeepButton({
  productId,
  bordered = false,
}: {
  productId: string;
  /** On a product page the action needs to look like one, rather than sitting
   *  in a column of captions reading as another label. */
  bordered?: boolean;
}) {
  const { profile, isLoading } = useSession();
  const { data: saved } = useSaved();
  const keep = useSaveProduct();
  const forget = useForgetProduct();

  const shape = bordered ? "inline-block border px-8 py-3.5" : "py-2";

  if (isLoading) {
    return <p className={`label text-muted ${bordered ? "px-8 py-3.5" : "py-2"}`}>&nbsp;</p>;
  }

  if (!profile) {
    return (
      <Link
        href="/login"
        className={`label text-muted transition-colors hover:text-ink ${shape} ${
          bordered ? "border-rule hover:border-ink" : ""
        }`}
      >
        Sign in to keep
      </Link>
    );
  }

  const isKept = saved?.some((item) => item.product_id === productId) ?? false;
  const busy = keep.isPending || forget.isPending;

  const tone = bordered
    ? isKept
      ? "border-hold text-hold hover:border-ink hover:text-ink"
      : "border-ink hover:bg-ink hover:text-paper"
    : isKept
      ? "text-hold hover:text-ink"
      : "text-muted hover:text-ink";

  return (
    <button
      onClick={() => (isKept ? forget.mutate(productId) : keep.mutate(productId))}
      disabled={busy}
      aria-pressed={isKept}
      className={`label transition-colors disabled:opacity-40 ${shape} ${tone}`}
    >
      {isKept ? "Kept" : "Keep"}
    </button>
  );
}

/** The mark itself: the same hairline every card carries, thickened and warmed
 *  once something is kept. Nothing is added to the layout, so a kept card and
 *  an unkept one sit at exactly the same size. */
export function KeepMark({ isKept }: { isKept: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`absolute inset-y-0 left-0 transition-all duration-300 ${
        isKept ? "w-[3px] bg-hold" : "w-px bg-rule"
      }`}
    />
  );
}
