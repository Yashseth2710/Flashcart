"use client";

import { AuthForm } from "@/components/auth/auth-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { RedirectWhenSignedIn } from "@/components/auth/redirect-when-signed-in";
import { HowHoldingWorks } from "@/components/auth/how-holding-works";
import { Field } from "@/components/ui/field";
import { useLogin } from "@/hooks/use-session";
import { loginSchema } from "@/lib/validation";

export default function LoginPage() {
  const { mutate, isPending, error } = useLogin();

  return (
    <>
      <RedirectWhenSignedIn />
      <AuthLayout eyebrow="Welcome back" title="Sign in" aside={<HowHoldingWorks />}>
      <AuthForm
        schema={loginSchema}
        onSubmit={mutate}
        isSubmitting={isPending}
        error={error}
        submitLabel="Sign in"
        footer={{ prompt: "No account yet?", href: "/register", action: "Create one" }}
      >
        {(errors) => (
          <>
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
              autoComplete="current-password"
              placeholder="••••••••"
              error={errors.password}
            />
          </>
        )}
      </AuthForm>
      </AuthLayout>
    </>
  );
}
