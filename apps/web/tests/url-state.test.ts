import { describe, expect, it } from "vitest";

import { readWorkspaceUrlState, safeInternalPath, updateWorkspaceUrl } from "../lib/url-state";

describe("workspace URL state", () => {
  it("round-trips filter and selected-course state without leaking unrelated params", () => {
    const initial = new URLSearchParams("q=prob&view=active&page=2");
    const next = updateWorkspaceUrl(initial, { query: "statistics", selected: "STAT-101" });

    expect(readWorkspaceUrlState(next)).toEqual({ query: "statistics", view: "active", selected: "STAT-101" });
    expect(next.get("page")).toBe("2");
  });

  it("removes default state and rejects external redirect targets", () => {
    const next = updateWorkspaceUrl(new URLSearchParams("q=old&view=active&selected=old"), {
      query: "",
      view: "all",
      selected: null,
    });

    expect(next.toString()).toBe("");
    expect(safeInternalPath("https://example.com", "/audit")).toBe("/audit");
    expect(safeInternalPath("//example.com", "/audit")).toBe("/audit");
    expect(safeInternalPath("/history")).toBe("/history");
  });
});
