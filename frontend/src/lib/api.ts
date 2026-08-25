import { z } from "zod";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** How long to wait, when the server has said to slow down. */
    readonly retryAfterSeconds?: number,
    /** The id the server logged this request under, worth showing only when
     *  there is nothing else useful to say. */
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Going too fast, rather than anything being wrong with the request. */
  get isTooManyAttempts(): boolean {
    return this.status === 429;
  }
}

/** Every refusal comes back in one shape, whichever layer refused it. The
 *  extra keys are optional so an older response still reads. */
const problemSchema = z.object({
  detail: z.string(),
  request_id: z.string().optional(),
});

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
    throw await readProblem(response);
  }

  if (response.status === 204) {
    return schema.parse(undefined);
  }

  return schema.parse(await response.json());
}

async function readProblem(response: Response): Promise<ApiError> {
  const retryAfter = Number(response.headers.get("Retry-After"));

  try {
    const parsed = problemSchema.safeParse(await response.json());
    if (parsed.success) {
      return new ApiError(
        parsed.data.detail,
        response.status,
        Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : undefined,
        parsed.data.request_id,
      );
    }
  } catch {
    // A response without a JSON body still needs something to show.
  }

  return new ApiError("Something went wrong. Try again.", response.status);
}
