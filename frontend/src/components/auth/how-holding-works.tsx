import { Logo } from "@/components/brand/logo";

const steps = [
  { label: "Reserve", detail: "One unit comes out of the pool and is put aside for you." },
  { label: "Decide", detail: "You have five minutes. Nobody else can take that unit." },
  { label: "Checkout", detail: "The hold becomes an order, or the time runs out and it goes back." },
] as const;

/** The three steps are a real sequence, which is why they are numbered. */
export function HowHoldingWorks() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-14 py-16 xl:px-20">
      <Logo withTagline className="mb-14" />

      <div className="max-w-sm">
        <p className="label text-muted">Why reserving matters</p>
        <p className="mt-5 font-display text-[1.6rem] leading-[1.35] text-ink">
          A sale of fifty units sells fifty units. Not fifty-one because two people clicked at
          the same moment.
        </p>

        <ol className="mt-10">
          {steps.map((step, index) => (
            <li key={step.label} className="flex gap-5 border-t border-rule py-4">
              <span className="tabular pt-0.5 text-xs text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="label text-ink">{step.label}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{step.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
