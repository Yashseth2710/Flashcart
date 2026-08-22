import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().min(1, "Enter your email address.").email("That is not an email address."),
  password: z.string().min(1, "Enter your password."),
});

export const registrationSchema = loginSchema.extend({
  name: z.string().trim().min(1, "Enter your name."),
  password: z.string().min(8, "Use at least 8 characters."),
});

export type FieldErrors = Record<string, string>;

export function collectErrors(error: z.ZodError): FieldErrors {
  return Object.fromEntries(
    error.issues.map((issue) => [String(issue.path[0]), issue.message]),
  );
}
