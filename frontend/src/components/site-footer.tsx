import Link from "next/link";

import { Logo } from "@/components/brand/logo";

/** The bottom of every page that has a top.
 *
 *  A shop that sells fixed runs against a clock owes the reader the rules in
 *  writing, somewhere that is always in the same place. So this is not a wall
 *  of links: it is the three rules that decide how a sale behaves, set
 *  where someone who has scrolled to the end of a sold-out sale will find them.
 *
 *  The lockup is the one already drawn for the brand, tagline and all. It has
 *  been sitting unused since it was made, and the foot of the page is where a
 *  full lockup belongs — the header only ever has room for the inline one.
 *
 *  It carries no top margin. The pages above already end with room of their
 *  own, and adding to it left a band of nothing between the last row of cards
 *  and the rule.
 */

const terms = [
  {
    term: "A hold is not a purchase",
    detail:
      "It puts one unit aside for five minutes. Let it run out and the unit goes back for someone else.",
  },
  {
    term: "Stock is counted once",
    detail:
      "However many people reach for the last one, exactly one of them gets it. The rest are told straight away.",
  },
  {
    term: "The clock is the clock",
    detail: "A sale opens and closes at the stated times. Nothing is extended.",
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-panel/40">
      <div className="px-6 py-16 sm:px-12">
        <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-3">
          {terms.map((rule) => (
            <div key={rule.term}>
              <dt className="label text-ink">{rule.term}</dt>
              <dd className="mt-3 max-w-xs text-sm leading-relaxed text-ink-soft">
                {rule.detail}
              </dd>
            </div>
          ))}
        </dl>

        <div className="mt-16 flex flex-col items-center gap-10 border-t border-rule pt-12 sm:flex-row sm:items-end sm:justify-between">
          <Logo withTagline />

          <nav className="label flex flex-wrap justify-center gap-x-8 gap-y-3 text-muted sm:justify-end">
            <Link href="/sales" className="transition-colors hover:text-ink">
              Sales
            </Link>
            <Link href="/products" className="transition-colors hover:text-ink">
              Shop
            </Link>
            <Link href="/account/holds" className="transition-colors hover:text-ink">
              Your holds
            </Link>
            <Link href="/account/orders" className="transition-colors hover:text-ink">
              Your orders
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
