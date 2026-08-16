import axe from "axe-core";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CourseCard, CreditLedger, GroupProgressTable, UnknownState } from "../components/ui";

describe("design system domain-neutral components", () => {
  it("renders evidence-oriented primitives without embedding eligibility rules", async () => {
    const { container } = render(
      <main>
        <CourseCard code="STAT-101" name="Curso de muestra" credits={3} status="unknown" />
        <CreditLedger earned={0} applied={0} unapplied={0} />
        <GroupProgressTable rows={[{ label: "Componente", completed: 0, required: 1, status: "unknown" }]} />
        <UnknownState description="La evidencia todavía no está disponible." />
      </main>,
    );
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
