"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { useLogout, useSession } from "@/hooks/use-session";
import { ApiError } from "@/lib/api";
import { changePassword, closeAccount, renameAccount, type Profile } from "@/lib/session";

export function AccountSettings() {
  const { profile } = useSession();

  if (!profile) {
    return null;
  }

  return (
    <>
      <header>
        <p className="font-script text-2xl leading-none text-ink-soft">Yours to change</p>
        <h1 className="mt-2 font-display text-4xl uppercase tracking-[0.045em]">Settings</h1>
      </header>

      <YourDetails profile={profile} />
      <ChangePassword />
      <LeavingSection profile={profile} />
    </>
  );
}

function YourDetails({ profile }: { profile: Profile }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const rename = useMutation({
    mutationFn: renameAccount,
    onSuccess: (updated) => {
      queryClient.setQueryData(["session"], updated);
      setEditing(false);
    },
    onSettled: () => {
      inFlight.current = false;
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current) return;

    const name = String(new FormData(event.currentTarget).get("name") ?? "").trim();
    if (!name) {
      setError("Enter a name.");
      return;
    }

    setError(null);
    inFlight.current = true;
    rename.mutate(name);
  }

  return (
    <section className="mt-14 border-t border-rule pt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h2 className="label text-muted">Your details</h2>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="label text-muted underline underline-offset-4 hover:text-ink"
          >
            Change your name
          </button>
        ) : null}
      </div>

      {editing ? (
        <form onSubmit={handleSubmit} noValidate className="mt-6 max-w-sm">
          <Field label="Name" name="name" defaultValue={profile.name} error={error ?? undefined} />
          {rename.error ? (
            <p role="alert" className="mt-4 border-l-2 border-reject pl-4 text-sm text-reject">
              {rename.error instanceof ApiError ? rename.error.message : "Could not save it."}
            </p>
          ) : null}
          <div className="mt-7 flex items-center gap-6">
            <Button type="submit" disabled={rename.isPending}>
              {rename.isPending ? "Saving" : "Save"}
            </Button>
            <button
              type="button"
              onClick={() => {
                setEditing(false);
                setError(null);
                rename.reset();
              }}
              className="label text-muted hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <dl className="mt-6 max-w-lg">
          <Row term="Name" value={profile.name} />
          <Row term="Email" value={profile.email} />
          <Row term="Account type" value={profile.role === "ADMIN" ? "Administrator" : "Customer"} />
          <Row term="With us since" value={new Date(profile.created_at).toLocaleDateString()} />
        </dl>
      )}
    </section>
  );
}

function ChangePassword() {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);
  const inFlight = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);

  const change = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setDone(true);
      formRef.current?.reset();
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

    if (!values.current_password) found.current_password = "Enter your current password.";
    if ((values.new_password ?? "").length < 8) {
      found.new_password = "Use at least 8 characters.";
    } else if (values.new_password === values.current_password) {
      found.new_password = "That is the password you already have.";
    }

    setErrors(found);
    setDone(false);
    if (Object.keys(found).length > 0) return;

    inFlight.current = true;
    change.mutate({
      current_password: values.current_password,
      new_password: values.new_password,
    });
  }

  return (
    <section className="mt-14 border-t border-rule pt-8">
      <h2 className="label text-muted">Password</h2>

      <form ref={formRef} onSubmit={handleSubmit} noValidate className="mt-6 max-w-sm space-y-7">
        <Field
          label="Current password"
          name="current_password"
          type="password"
          autoComplete="current-password"
          error={errors.current_password}
        />
        <Field
          label="New password"
          name="new_password"
          type="password"
          autoComplete="new-password"
          placeholder="At least 8 characters"
          error={errors.new_password}
        />

        {change.error ? (
          <p role="alert" className="border-l-2 border-reject pl-4 text-sm text-reject">
            {change.error instanceof ApiError ? change.error.message : "Could not change it."}
          </p>
        ) : null}

        {done ? <p className="text-sm text-fill">Your password has been changed.</p> : null}

        <Button type="submit" disabled={change.isPending}>
          {change.isPending ? "Changing" : "Change password"}
        </Button>
      </form>
    </section>
  );
}

function LeavingSection({ profile }: { profile: Profile }) {
  const router = useRouter();
  const { mutate: signOut, isPending: signingOut } = useLogout();
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");

  const close = useMutation({
    mutationFn: closeAccount,
    onSuccess: () => {
      router.push("/");
      router.refresh();
    },
  });

  const matches = typed.trim().toLowerCase() === profile.email.toLowerCase();

  return (
    <section className="mt-14 border-t border-rule pt-8">
      <h2 className="label text-muted">Leaving</h2>

      <div className="mt-6 flex flex-wrap items-center gap-8">
        <button
          onClick={() => signOut()}
          disabled={signingOut}
          className="label border border-ink px-8 py-3.5 transition-colors hover:bg-ink hover:text-paper"
        >
          {signingOut ? "Signing out" : "Sign out"}
        </button>

        {!confirming ? (
          <button
            onClick={() => setConfirming(true)}
            className="label text-muted underline underline-offset-4 transition-colors hover:text-reject"
          >
            Delete this account
          </button>
        ) : null}
      </div>

      {confirming ? (
        <div className="mt-10 max-w-sm border-l-2 border-reject pl-5">
          <p className="text-sm leading-relaxed text-ink-soft">
            Deleting cannot be undone. Any hold you have goes back to its sale. Type{" "}
            <span className="tabular text-ink">{profile.email}</span> to confirm.
          </p>

          <input
            type="email"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            aria-label="Type your email to confirm"
            placeholder={profile.email}
            className="tabular mt-5 w-full border-b border-rule bg-transparent pb-2 text-sm
                       outline-none transition-colors placeholder:text-muted/50 focus:border-ink"
          />

          {close.error ? (
            <p role="alert" className="mt-5 text-sm text-reject">
              {close.error instanceof ApiError ? close.error.message : "Could not delete it."}
            </p>
          ) : null}

          <div className="mt-7 flex items-center gap-6">
            <button
              onClick={() => close.mutate(typed.trim())}
              disabled={!matches || close.isPending}
              className="label bg-reject px-8 py-3.5 text-paper transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
            >
              {close.isPending ? "Deleting" : "Delete for good"}
            </button>
            <button
              onClick={() => {
                setConfirming(false);
                setTyped("");
                close.reset();
              }}
              className="label text-muted hover:text-ink"
            >
              Keep it
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-rule py-3.5">
      <dt className="label text-muted">{term}</dt>
      <dd className="tabular text-sm text-ink">{value}</dd>
    </div>
  );
}
