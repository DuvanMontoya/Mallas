import {
  createApiClient,
  type ApiComponents,
  type ApiPaths,
} from "@curriculum-navigator/api-client";

export type UserView = ApiComponents["schemas"]["UserView"];
export type ProblemDetails = ApiComponents["schemas"]["ProblemDetails"];

export type SessionState = "authenticated" | "anonymous" | "unavailable";

export interface SessionSnapshot {
  state: SessionState;
  user: UserView | null;
  correlationId: string | null;
}

export interface ApiFailure {
  problem: ProblemDetails | null;
  correlationId: string | null;
  unavailable: boolean;
}

const api = createApiClient();

function correlationId(response: Response | undefined): string | null {
  return response?.headers.get("X-Request-ID") ?? null;
}

function isProblemDetails(value: unknown): value is ProblemDetails {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ProblemDetails>;
  return typeof candidate.code === "string" && typeof candidate.detail === "string";
}

export function problemFromUnknown(value: unknown): ProblemDetails | null {
  return isProblemDetails(value) ? value : null;
}

export function problemMessage(problem: ProblemDetails | null, fallback: string): string {
  return problem?.detail || fallback;
}

export async function getSessionSnapshot(headers?: HeadersInit): Promise<SessionSnapshot> {
  try {
    const result = await api.GET("/api/v1/auth/me", { headers });
    const requestCorrelationId = correlationId(result.response);
    if (result.response.status === 401) {
      return { state: "anonymous", user: null, correlationId: requestCorrelationId };
    }
    if (result.data) {
      return { state: "authenticated", user: result.data, correlationId: requestCorrelationId };
    }
    return { state: "unavailable", user: null, correlationId: requestCorrelationId };
  } catch {
    return { state: "unavailable", user: null, correlationId: null };
  }
}

export async function getCsrfToken(): Promise<string> {
  const result = await api.GET("/api/v1/auth/csrf");
  if (!result.data) {
    throw new Error(problemMessage(problemFromUnknown(result.error), "CSRF token unavailable."));
  }
  return result.data.csrf_token;
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ user: UserView } | { failure: ApiFailure }> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.POST("/api/v1/auth/login", {
      body: { email, password },
      headers: { "X-CSRFToken": csrfToken },
    });
    if (result.data) return { user: result.data.user };
    return {
      failure: {
        problem: problemFromUnknown(result.error),
        correlationId: correlationId(result.response),
        unavailable: false,
      },
    };
  } catch {
    return { failure: { problem: null, correlationId: null, unavailable: true } };
  }
}

export async function signOut(): Promise<ApiFailure | null> {
  try {
    const csrfToken = await getCsrfToken();
    const result = await api.POST("/api/v1/auth/logout", {
      headers: { "X-CSRFToken": csrfToken },
    });
    if (!result.error) return null;
    return {
      problem: problemFromUnknown(result.error),
      correlationId: correlationId(result.response),
      unavailable: false,
    };
  } catch {
    return { problem: null, correlationId: null, unavailable: true };
  }
}

export type ApiPath = keyof ApiPaths;
