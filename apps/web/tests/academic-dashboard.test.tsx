import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AcademicDashboard } from "../components/academic-dashboard";
import type { AcademicOverview } from "../lib/api";
import fixture from "./e2e/fixtures/student-academic-overview.json";

describe("academic dashboard read model", () => {
  it("presents backend statuses, UNKNOWN and the credit-only disclaimer", () => {
    render(<AcademicDashboard overview={fixture as AcademicOverview} />);

    expect(screen.getByRole("heading", { name: /créditos por completar/i })).toBeInTheDocument();
    expect(screen.getByText(/aprobar créditos no certifica por sí solo el grado/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /graduation:foreign_language_b1/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /1000003.*álgebra lineal/i })).toHaveAttribute(
      "href",
      "/curriculum?selected=1000003",
    );
  });

  it("has no serious automated accessibility violations", async () => {
    const { container } = render(<AcademicDashboard overview={fixture as AcademicOverview} />);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
