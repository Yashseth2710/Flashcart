"use client";

import Link from "next/link";

import { useForgetSale, useRemindMe, useReminders } from "@/hooks/use-saved";
import { useSession } from "@/hooks/use-session";
import { ApiError } from "@/lib/api";

/** Marking a sale to be shown on the way back in.
 *
 * Nothing is sent anywhere: the mark is read when they next arrive and turned
 * into what is on the screen. The wording says so plainly rather than promising
 * a message that will never come. */
export function RemindButton({ saleId }: { saleId: string }) {
  const { profile, isLoading } = useSession();
  const { data: reminders } = useReminders();
  const remind = useRemindMe();
  const forget = useForgetSale();

  if (isLoading) {
    return <p className="label py-3 text-muted">&nbsp;</p>;
  }

  if (!profile) {
    return (
      <Link
        href="/login"
        className="label inline-block border border-rule px-6 py-3 text-muted
                   transition-colors hover:border-ink hover:text-ink"
      >
        Sign in to mark it
      </Link>
    );
  }

  const isMarked = reminders?.some((reminder) => reminder.sale_id === saleId) ?? false;
  const busy = remind.isPending || forget.isPending;
  const failure = remind.error ?? forget.error;

  return (
    <div>
      <button
        onClick={() => (isMarked ? forget.mutate(saleId) : remind.mutate(saleId))}
        disabled={busy}
        aria-pressed={isMarked}
        className={`label inline-block border px-6 py-3 transition-colors disabled:opacity-40 ${
          isMarked
            ? "border-hold text-hold hover:border-ink hover:text-ink"
            : "border-ink hover:bg-ink hover:text-paper"
        }`}
      >
        {isMarked ? "On your list" : "Add to your list"}
      </button>

      {failure ? (
        <p role="alert" className="mt-3 max-w-xs text-xs leading-relaxed text-reject">
          {failure instanceof ApiError ? failure.message : "Could not mark it."}
        </p>
      ) : null}
    </div>
  );
}
