"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { type FieldErrors, collectErrors } from "@/lib/validation";
import type { ZodType, z } from "zod";

type Props<S extends ZodType> = {
  schema: S;
  onSubmit: (values: z.output<S>) => void;
  isSubmitting: boolean;
  error: unknown;
  submitLabel: string;
  footer: { prompt: string; href: string; action: string };
  children: (errors: FieldErrors) => React.ReactNode;
};

export function AuthForm<S extends ZodType>({
  schema,
  onSubmit,
  isSubmitting,
  error,
  submitLabel,
  footer,
  children,
}: Props<S>) {
  const [errors, setErrors] = useState<FieldErrors>({});
  // React state does not update until the next render, so two clicks in the
  // same tick would both pass an isSubmitting check. A ref updates at once.
  const inFlight = useRef(false);

  useEffect(() => {
    if (!isSubmitting) {
      inFlight.current = false;
    }
  }, [isSubmitting]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) {
      return;
    }
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const parsed = schema.safeParse(values);

    if (!parsed.success) {
      setErrors(collectErrors(parsed.error));
      return;
    }

    setErrors({});
    inFlight.current = true;
    onSubmit(parsed.data);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-10">
      <div className="space-y-7">{children(errors)}</div>

      {error ? (
        <p role="alert" className="mt-6 border-l-2 border-reject pl-4 text-sm text-reject">
          {error instanceof ApiError ? error.message : "Something went wrong. Try again."}
        </p>
      ) : null}

      <Button type="submit" disabled={isSubmitting} className="mt-10 w-full">
        {isSubmitting ? "One moment" : submitLabel}
      </Button>

      <p className="mt-8 text-sm text-muted">
        {footer.prompt}{" "}
        <Link href={footer.href} className="text-ink underline underline-offset-4">
          {footer.action}
        </Link>
      </p>
    </form>
  );
}
