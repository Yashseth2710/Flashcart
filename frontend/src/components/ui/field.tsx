import type { InputHTMLAttributes } from "react";
import { useId } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export function Field({ label, error, className = "", ...props }: Props) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div className={className}>
      <label htmlFor={id} className="label block text-muted">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className="mt-2 w-full border-b border-rule bg-transparent pb-2.5 text-[0.95rem] leading-6
                   text-ink outline-none transition-colors placeholder:text-muted/60
                   focus:border-ink aria-[invalid]:border-reject"
        {...props}
      />
      {error ? (
        <p id={errorId} className="mt-2 text-xs text-reject">
          {error}
        </p>
      ) : null}
    </div>
  );
}
