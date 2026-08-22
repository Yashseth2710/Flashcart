"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { createSale } from "@/lib/admin";
import { ApiError } from "@/lib/api";

/** A datetime-local value is wall-clock with no zone; the browser's own offset
 *  turns it into the moment the person meant. */
function toInstant(local: string): string {
  return new Date(local).toISOString();
}

function defaultStart(): string {
  const soon = new Date(Date.now() + 60 * 60 * 1000);
  soon.setSeconds(0, 0);
  return new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function NewSaleForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inFlight = useRef(false);

  const create = useMutation({
    mutationFn: createSale,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-sales"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      onDone();
    },
    onSettled: () => {
      inFlight.current = false;
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;

    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;
    const found: Record<string, string> = {};

    if (!values.name?.trim()) found.name = "Give the sale a name.";
    if (!values.start_time) found.start_time = "Say when it opens.";
    if (!values.end_time) found.end_time = "Say when it closes.";
    if (
      values.start_time &&
      values.end_time &&
      new Date(values.end_time) <= new Date(values.start_time)
    ) {
      found.end_time = "It has to close after it opens.";
    }

    setErrors(found);
    if (Object.keys(found).length > 0) return;

    inFlight.current = true;
    create.mutate({
      name: values.name.trim(),
      description: values.description?.trim() || null,
      start_time: toInstant(values.start_time),
      end_time: toInstant(values.end_time),
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mb-14 border-y border-rule py-10">
      <p className="label text-muted">New sale</p>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
        Set the window first. Products and their allocations are added afterwards, and can only
        be changed until the sale opens.
      </p>

      <div className="mt-8 grid max-w-2xl gap-7 sm:grid-cols-2">
        <Field label="Name" name="name" placeholder="Tech Rush" error={errors.name} />
        <Field label="Description" name="description" placeholder="Optional" />
        <Field
          label="Opens"
          name="start_time"
          type="datetime-local"
          defaultValue={defaultStart()}
          error={errors.start_time}
        />
        <Field label="Closes" name="end_time" type="datetime-local" error={errors.end_time} />
      </div>

      {create.error ? (
        <p role="alert" className="mt-6 border-l-2 border-reject pl-4 text-sm text-reject">
          {create.error instanceof ApiError ? create.error.message : "Could not plan it."}
        </p>
      ) : null}

      <Button type="submit" disabled={create.isPending} className="mt-9">
        {create.isPending ? "Planning" : "Plan the sale"}
      </Button>
    </form>
  );
}
