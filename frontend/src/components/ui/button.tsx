import type { ButtonHTMLAttributes } from "react";

type Variant = "solid" | "outline";

const base =
  "label inline-flex items-center justify-center px-8 py-3.5 transition-colors " +
  "disabled:cursor-not-allowed disabled:opacity-45";

const variants: Record<Variant, string> = {
  solid: "bg-ink text-paper hover:bg-ink-soft",
  outline: "border border-ink text-ink hover:bg-ink hover:text-paper",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant };

export function Button({ variant = "solid", className = "", ...props }: Props) {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}
