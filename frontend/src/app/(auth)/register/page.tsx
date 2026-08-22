"use client";

import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { RedirectWhenSignedIn } from "@/components/auth/redirect-when-signed-in";
import { HowHoldingWorks } from "@/components/auth/how-holding-works";
import { Field } from "@/components/ui/field";
import { useRegister } from "@/hooks/use-session";
import { registrationSchema } from "@/lib/validation";

export default function RegisterPage() {
  const { mutate, isPending, error } = useRegister();

  return (
    <>
      <RedirectWhenSignedIn />
      <AuthLayout eyebrow="First time here" title="Create account" aside={<HowHoldingWorks />}>
      <AuthForm
        schema={registrationSchema}
        onSubmit={mutate}
        isSubmitting={isPending}
        error={error}
        submitLabel="Create account"
        footer={{ prompt: "Already have an account?", href: "/login", action: "Sign in" }}
      >
        {(errors) => (
          <>
            <Field label="Name" name="name" autoComplete="name" placeholder="Ada Lovelace" error={errors.name} />
            <Field
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              error={errors.email}
            />
            <Field
              label="Password"
              name="password"
              type="password"
              autoComplete="new-password"
              placeholder="At least 8 characters"
              error={errors.password}
            />
          </>
        )}
      </AuthForm>
      </AuthLayout>
    </>
  );
}
