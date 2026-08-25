type Props = {
  /** The full lockup adds the rule-and-tagline line beneath the wordmark. */
  withTagline?: boolean;
  className?: string;
};

/** The cart leans forward and trails motion lines: something moving off the shelf. */
function CartMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 40"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M2 14h16M8 21h12M14 28h8" />
      <path d="M25 6h6l3 8m0 0 4 13h17l6-13H34Z" />
      <circle cx="40" cy="34" r="3.2" />
      <circle cx="52" cy="34" r="3.2" />
    </svg>
  );
}

export function Logo({ withTagline = false, className = "" }: Props) {
  return (
    <span className={`inline-flex flex-col items-center ${className}`}>
      <CartMark className="h-7 w-11 text-hold" />
      <span className="mt-2 font-display text-3xl tracking-[0.14em] text-ink">FlashCart</span>
      {withTagline ? (
        /* The rules need room of their own. Sized to the words plus the length
           of two visible lines, rather than to the words alone: at the tighter
           width the gaps ate the remainder and both rules came out at nothing. */
        <span className="mt-2.5 flex w-full min-w-[19rem] items-center gap-3">
          <span className="h-px flex-1 bg-hold/50" />
          <span className="label whitespace-nowrap text-[0.6rem] text-ink-soft">
            Limited stock. Held fairly.
          </span>
          <span className="h-px flex-1 bg-hold/50" />
        </span>
      ) : null}
    </span>
  );
}

/** The header needs the mark and name on one line, at reading size. */
export function LogoInline({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <CartMark className="h-4 w-6 text-hold" />
      <span className="font-display text-xl tracking-[0.08em] text-ink">FlashCart</span>
    </span>
  );
}
