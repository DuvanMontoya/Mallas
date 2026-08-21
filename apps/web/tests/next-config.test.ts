import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("security response headers", () => {
  it("prevents reset tokens from being sent as a referrer", async () => {
    const rules = await nextConfig.headers?.();
    const resetRule = rules?.find((rule) => rule.source === "/reset-password");

    expect(resetRule?.headers).toContainEqual({ key: "Referrer-Policy", value: "no-referrer" });
  });
});
