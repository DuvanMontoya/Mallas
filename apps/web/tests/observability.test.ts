import { afterEach, describe, expect, it, vi } from "vitest";

import { reportFrontendError, reportWebVital } from "@/lib/observability";

describe("frontend observability adapter", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("does not send telemetry until an explicit endpoint is configured", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    expect(reportFrontendError(new Error("student@example.edu token=secret"))).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("sends a redacted error envelope without the original message or credentials", () => {
    vi.stubEnv("NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT", "https://telemetry.example/errors?api_key=secret");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 202 }));

    expect(
      reportFrontendError(new Error("student@example.edu bearer very-secret"), {
        component: "planner",
        digest: "digest-12345678",
      }),
    ).toBe(true);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [endpoint, init] = fetchSpy.mock.calls[0];
    expect(String(endpoint)).toBe("https://telemetry.example/errors");
    expect(init?.credentials).toBe("omit");
    const body = String(init?.body);
    expect(body).not.toContain("student@example.edu");
    expect(body).not.toContain("very-secret");
    expect(body).toContain('"error_type":"Error"');
  });

  it("bounds and sends web vital values", () => {
    vi.stubEnv("NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT", "https://telemetry.example/vitals");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 202 }));

    expect(reportWebVital({ name: "LCP", value: 99999999, delta: -99999999 })).toBe(true);

    const body = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body)) as {
      metric: { value: number; delta: number };
    };
    expect(body.metric.value).toBe(3600000);
    expect(body.metric.delta).toBe(-3600000);
  });
});
