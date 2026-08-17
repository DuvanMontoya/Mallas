import { beforeEach, describe, expect, it, vi } from "vitest";

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }));

vi.mock("@curriculum-navigator/api-client", () => ({
  createApiClient: () => ({ GET: getMock }),
}));

import { getDependencyGraph, getInstitutionalAnalytics, getNotifications, getStudentAnalytics } from "../lib/api";

describe("frontend API adapter", () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockResolvedValue({ data: {}, response: new Response() });
  });

  it("serializes dependency-graph filters under openapi-fetch params.query", async () => {
    await getDependencyGraph({
      planCode: "2514",
      revisionId: "revision-1",
      enrollmentId: "enrollment-1",
      termCode: "2026-1",
      selected: "2016379",
      headers: { Cookie: "session=opaque" },
    });

    expect(getMock).toHaveBeenCalledWith("/api/v1/dependency-graph", {
      headers: { Cookie: "session=opaque" },
      params: {
        query: {
          plan_code: "2514",
          revision_id: "revision-1",
          enrollment_id: "enrollment-1",
          term_code: "2026-1",
          selected: "2016379",
        },
      },
    });
  });

  it("serializes notification feed filters under the generated contract", async () => {
    await getNotifications({ unreadOnly: true, limit: 20, before: "opaque-cursor" });

    expect(getMock).toHaveBeenCalledWith("/api/v1/notifications", {
      headers: undefined,
      params: { query: { unread_only: true, limit: 20, before: "opaque-cursor" } },
    });
  });

  it("serializes student analytics filters under the generated contract", async () => {
    await getStudentAnalytics({ enrollmentId: "enrollment-1", headers: { Cookie: "session=opaque" } });

    expect(getMock).toHaveBeenCalledWith("/api/v1/analytics/student", {
      headers: { Cookie: "session=opaque" },
      params: { query: { enrollment_id: "enrollment-1" } },
    });
  });

  it("serializes institutional analytics scope and privacy threshold", async () => {
    await getInstitutionalAnalytics({
      institutionId: "institution-1",
      programId: "program-1",
      termCode: "2026-2",
      minCellSize: 8,
    });

    expect(getMock).toHaveBeenCalledWith("/api/v1/analytics/institutional", {
      headers: undefined,
      params: {
        query: {
          institution_id: "institution-1",
          program_id: "program-1",
          term_code: "2026-2",
          min_cell_size: 8,
        },
      },
    });
  });
});
