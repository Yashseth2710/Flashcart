"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { ApiError } from "@/lib/api";
import { createProduct } from "@/lib/admin";

export function NewProductForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inFlight = useRef(false);

  const create = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-products"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
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

    if (!values.name?.trim()) found.name = "Give it a name.";
    const price = Number(values.base_price);
    if (!values.base_price || !Number.isFinite(price) || price < 0) {
      found.base_price = "Enter a price of zero or more.";
    }

    setErrors(found);
    if (Object.keys(found).length > 0) return;

    inFlight.current = true;
    create.mutate({
      name: values.name.trim(),
      base_price: price.toFixed(2),
      category: values.category?.trim() || null,
      brand: values.brand?.trim() || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mb-14 border-y border-rule py-10">
      <p className="label text-muted">New product</p>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
        It arrives with no stock and hidden from nobody — set a quantity below once it exists.
      </p>

      <div className="mt-8 grid max-w-2xl gap-7 sm:grid-cols-2">
        <Field label="Name" name="name" placeholder="Brass table lamp" error={errors.name} />
        <Field label="Price" name="base_price" inputMode="decimal" placeholder="49.50" error={errors.base_price} />
        <Field label="Category" name="category" placeholder="home-decoration" />
        <Field label="Brand" name="brand" placeholder="FlashCart" />
      </div>

      {create.error ? (
        <p role="alert" className="mt-6 border-l-2 border-reject pl-4 text-sm text-reject">
          {create.error instanceof ApiError ? create.error.message : "Could not add it."}
        </p>
      ) : null}

      <Button type="submit" disabled={create.isPending} className="mt-9">
        {create.isPending ? "Adding" : "Add product"}
      </Button>
    </form>
  );
}
