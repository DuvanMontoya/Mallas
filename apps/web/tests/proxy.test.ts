import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "../proxy";

describe("product route proxy", () => {
  it("redirects a request without a session cookie to login and preserves its internal destination", () => {
    const response = proxy(new NextRequest("https://navigator.test/curriculum?selected=1000003"));

    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
      "https://navigator.test/login?next=%2Fcurriculum%3Fselected%3D1000003",
    );
  });

  it("does not treat the proxy as the authoritative validator when a cookie is present", () => {
    const request = new NextRequest("https://navigator.test/curriculum", {
      headers: { Cookie: "curriculum_session=opaque" },
    });

    expect(proxy(request).headers.get("x-middleware-next")).toBe("1");
  });
});
