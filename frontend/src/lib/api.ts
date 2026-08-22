import { z } from "zod";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const problemSchema = z.object({ detail: z.string() });

type RequestOptions = {
  method?: string;
  body?: unknown;
};

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  { method = "GET", body }: RequestOptions = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method,
    // Sends and stores the session cookie, which the browser will not do
    // across origins without being told to.
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(await readMessage(response), response.status);
  }

  if (response.status === 204) {
    return schema.parse(undefined);
  }

  return schema.parse(await response.json());
}

async function readMessage(response: Response): Promise<string> {
  try {
    const parsed = problemSchema.safeParse(await response.json());
    if (parsed.success) {
      return parsed.data.detail;
    }
  } catch {
    // A response without a JSON body still needs something to show.
  }
  return "Something went wrong. Try again.";
}
