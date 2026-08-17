import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalyticsDashboard } from "../components/analytics-dashboard";
import type { StudentAnalytics } from "../lib/api";

const fixture = {
  schema_version: "1.0",
  scope: "STUDENT",
  data_state: "PERSISTED_PUBLISHED_AUDIT",
  as_of: "2026-08-16T12:00:00Z",
  enrollment_id: "00000000-0000-0000-0000-000000000001",
  program_code: "STAT",
  program_name: "Statistics",
  plan_code: "2514",
  revision_code: "2023",
  snapshot: { status: "INCOMPLETE", engine_version: "audit-engine/1" },
  metrics: {
    credits: { required: 141, applied: 64, remaining: 77, progress_percent: 45 },
    requirements: {
      remaining_count: 2,
      unknown_count: 1,
      remaining: [{ code: "GRADUATION:B1", purpose: "GRADUATION", status: "UNKNOWN" }],
    },
    critical_courses: [{ course_code: "STAT204", state: "BLOCKED", requirement_codes: ["PREREQ:STAT204"] }],
    trend: [{ captured_at: "2026-08-16T12:00:00Z", result_hash: "abc", applied_credits: 64, required_credits: 141, progress_percent: 45, status: "INCOMPLETE", unknown_count: 1 }],
    scenarios: [{ name: "Ruta equilibrada", planned_course_count: 3, progress_percent: 58, unknown_count: 0, generated_at: "2026-08-15T12:00:00Z" }],
  },
  definitions: [{ key: "credits.applied", label: "Créditos aplicados", description: "Derivado", source: "DegreeAuditResult", epistemic_status: "DERIVED", privacy: "PRIVATE" }],
  warnings: [],
} as StudentAnalytics;

describe("analytics dashboard", () => {
  it("renders audited progress, bottlenecks, scenarios and definitions", () => {
    render(<AnalyticsDashboard analytics={fixture} failure={null} />);

    expect(screen.getByRole("heading", { name: /evolución académica/i })).toBeInTheDocument();
    expect(screen.getAllByText("64 / 141").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("STAT204")).toBeInTheDocument();
    expect(screen.getByText("Ruta equilibrada")).toBeInTheDocument();
    expect(screen.getByText(/cómo se calculan estas métricas/i)).toBeInTheDocument();
  });

  it("has no serious automated accessibility violations", async () => {
    const { container } = render(<AnalyticsDashboard analytics={fixture} failure={null} />);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
