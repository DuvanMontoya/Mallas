import axe from "axe-core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OfferingsExplorer } from "../components/offerings-explorer";
import type { OfferingsReadModel } from "../lib/api";
import fixture from "./e2e/fixtures/offerings.json";

vi.mock("next/navigation", () => ({
  usePathname: () => "/offerings",
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("offerings explorer", () => {
  it("separates offer, academic eligibility, freshness and unknown capacity", () => {
    render(
      <OfferingsExplorer
        data={fixture as OfferingsReadModel}
        schedule={null}
        selectedSectionIds={[]}
      />,
    );

    expect(screen.getByRole("heading", { name: "2026-2S" })).toBeInTheDocument();
    expect(screen.getAllByText(/fuente fresca/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Elegibilidad: Puedes cursarla")).toBeInTheDocument();
    expect(screen.getByText("Elegibilidad: Prerrequisitos pendientes")).toBeInTheDocument();
    expect(screen.getAllByText(/dato no reportado/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Oferta: Con grupos reportados").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /cálculo diferencial/i })).toHaveAttribute(
      "href",
      "/curriculum?selected=2016377",
    );
  });

  it("renders exact conflict occurrences from the backend read model", () => {
    render(
      <OfferingsExplorer
        data={fixture as OfferingsReadModel}
        schedule={{
          term_code: "2026-2S",
          section_ids: ["00000000-0000-4000-8000-000000000421", "00000000-0000-4000-8000-000000000422"],
          state: "CONFLICT",
          conflicts: [
            {
              left_section_id: "00000000-0000-4000-8000-000000000421",
              right_section_id: "00000000-0000-4000-8000-000000000422",
              left_meeting_id: "00000000-0000-4000-8000-000000000431",
              right_meeting_id: "00000000-0000-4000-8000-000000000432",
              occurrence_date: "2026-08-10",
              starts_at_utc: "2026-08-10T13:00:00Z",
              ends_at_utc: "2026-08-10T15:00:00Z",
              reason: "OVERLAP",
            },
          ],
          unknown_reasons: [],
        }}
        selectedSectionIds={["00000000-0000-4000-8000-000000000421", "00000000-0000-4000-8000-000000000422"]}
      />,
    );

    expect(screen.getByRole("heading", { name: /hay solapamientos/i })).toBeInTheDocument();
    expect(screen.getByText(/se solapan/i)).toBeInTheDocument();
    expect(screen.getByText("2026-08-10")).toBeInTheDocument();
  });

  it("distinguishes reported capacity from real-time capacity", () => {
    const known = structuredClone(fixture) as OfferingsReadModel;
    known.courses[0].sections[0].capacity.state = "REPORTED_NOT_REAL_TIME";
    known.courses[1].sections[0].capacity.state = "REAL_TIME";
    render(<OfferingsExplorer data={known} schedule={null} selectedSectionIds={[]} />);
    expect(screen.getByText("Cupo: Reportado, no en tiempo real")).toBeInTheDocument();
    expect(screen.getByText("Cupo: Actualizado en tiempo real")).toBeInTheDocument();
  });

  it("has no serious automated accessibility violations", async () => {
    const { container } = render(
      <OfferingsExplorer data={fixture as OfferingsReadModel} schedule={null} selectedSectionIds={[]} />,
    );
    expect((await axe.run(container)).violations).toEqual([]);
  });
});
