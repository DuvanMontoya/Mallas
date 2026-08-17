export type WebVitalMetric = {
  name: string;
  value: number;
  delta?: number;
  id?: string;
  rating?: string;
};

type TelemetryPayload = {
  event: "frontend.error" | "frontend.web_vital";
  timestamp: string;
  error_type?: string;
  digest?: string;
  route?: string;
  metric?: WebVitalMetric;
  context?: Record<string, string>;
};

const EMAIL_PATTERN = /\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/g;
const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+/=-]+/gi;
const UUID_PATTERN = /\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/gi;
const LONG_NUMERIC_PATTERN = /\b\d{6,}\b/g;

function sanitizeText(value: string): string {
  return value
    .replace(BEARER_PATTERN, "[REDACTED]")
    .replace(EMAIL_PATTERN, "[REDACTED]")
    .replace(UUID_PATTERN, "[ID]")
    .replace(LONG_NUMERIC_PATTERN, ":id")
    .slice(0, 240);
}

function sanitizeMetricId(value: string): string {
  return sanitizeText(value.split(/[?#]/, 1)[0]).replace(/[^A-Za-z0-9._:-]/g, "").slice(0, 120);
}

function safeRoute(): string | undefined {
  if (typeof window === "undefined") return undefined;
  const segments = window.location.pathname
    .split("/")
    .filter(Boolean)
    .map((segment) => sanitizeText(segment).replace(/[^A-Za-z0-9._:-]/g, ":segment"));
  return `/${segments.join("/")}`;
}

function errorType(error: unknown): string {
  if (error instanceof Error && error.name) return sanitizeText(error.name);
  if (error && typeof error === "object" && "name" in error && typeof error.name === "string") {
    return sanitizeText(error.name);
  }
  return "UnknownError";
}

function safeContext(context: Record<string, unknown>): Record<string, string> {
  const allowed = new Set(["component", "feature", "phase", "digest", "correlation_id"]);
  return Object.fromEntries(
    Object.entries(context)
      .filter(([key, value]) => allowed.has(key) && typeof value === "string")
      .map(([key, value]) => [key, sanitizeText(value as string)]),
  );
}

function reportingEndpoint(): string | null {
  const configured = process.env.NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT;
  if (!configured) return null;
  try {
    const url = new URL(configured);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return null;
  }
}

function send(payload: TelemetryPayload): boolean {
  const endpoint = reportingEndpoint();
  if (!endpoint || typeof fetch !== "function") return false;
  void fetch(endpoint, {
    method: "POST",
    credentials: "omit",
    keepalive: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).catch(() => undefined);
  return true;
}

export function reportFrontendError(
  error: unknown,
  context: Record<string, unknown> = {},
): boolean {
  return send({
    event: "frontend.error",
    timestamp: new Date().toISOString(),
    error_type: errorType(error),
    digest: typeof context.digest === "string" ? sanitizeText(context.digest) : undefined,
    route: safeRoute(),
    context: safeContext(context),
  });
}

export function reportWebVital(metric: WebVitalMetric): boolean {
  if (!metric.name || !Number.isFinite(metric.value)) return false;
  return send({
    event: "frontend.web_vital",
    timestamp: new Date().toISOString(),
    route: safeRoute(),
    metric: {
      name: sanitizeText(metric.name),
      value: Math.max(0, Math.min(metric.value, 3600000)),
      ...(metric.delta !== undefined && Number.isFinite(metric.delta)
        ? { delta: Math.max(-3600000, Math.min(metric.delta, 3600000)) }
        : {}),
      ...(metric.id ? { id: sanitizeMetricId(metric.id) } : {}),
      ...(metric.rating ? { rating: sanitizeText(metric.rating) } : {}),
    },
  });
}
