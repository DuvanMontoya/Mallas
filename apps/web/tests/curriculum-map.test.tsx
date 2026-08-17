import axe from "axe-core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CurriculumMapPage } from "../components/curriculum-map";
import type { CurriculumMap } from "../lib/api";
import fixture from "./e2e/fixtures/curriculum-map.json";

vi.mock("next/navigation", () => ({
  usePathname: () => "/curriculum",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("curriculum map read model and interaction", () => {
  beforeEach(() => window.localStorage.clear());

  it("opens with the student's decisions and separates mandatory courses from choice pools", () => {
    render(<CurriculumMapPage map={fixture as CurriculumMap} />);

    expect(screen.getByRole("heading", { name: /malla curricular/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /qué puedes matricular ahora/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /las obligatorias que sostienen el plan/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /escoge dentro de cada agrupación/i })).toBeInTheDocument();
    expect(screen.getByText(/no debes cursar todas estas asignaturas/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /1000003.*álgebra lineal/i }).length).toBeGreaterThan(0);
    expect(screen.getByText(/no semestres oficiales/i)).toBeInTheDocument();
  });

  it("separates a published revision from its non-normative visual layout", () => {
    const publishedMap = structuredClone(fixture);
    publishedMap.revision.status = "PUBLISHED";
    publishedMap.revision.normative = false;
    publishedMap.warnings = publishedMap.warnings.filter(
      (warning) => warning !== "CURRICULUM_REVISION_NOT_PUBLISHED",
    );

    render(<CurriculumMapPage map={publishedMap as CurriculumMap} />);

    expect(screen.getByText("Revisión publicada")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /nivel de dependencias.*no normativo/i })).toBeInTheDocument();
    expect(screen.queryByText(/revisión en proceso editorial/i)).not.toBeInTheDocument();
  });

  it("selects a course, highlights only direct context and filters by state", () => {
    render(<CurriculumMapPage map={fixture as CurriculumMap} />);

    fireEvent.click(screen.getAllByRole("button", { name: /1000003.*álgebra lineal/i })[0]);
    expect(screen.getByRole("heading", { name: "Álgebra lineal", level: 2 })).toBeInTheDocument();
    expect(screen.getByText(/requisitos para cursarla/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /1000002/i }).length).toBeGreaterThan(0);
    expect(document.querySelectorAll('[data-course-code="2000001"]')[0]).toHaveClass("decision-context-unlock");
    expect(screen.getByText(/fuera del contexto seleccionado/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Estado personal"), { target: { value: "ELIGIBLE" } });
    expect(screen.getByText("1 cursos visibles · 3 en la revisión")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /1000003.*álgebra lineal/i }).length).toBeGreaterThan(0);
    expect(within(screen.getByRole("region", { name: /las obligatorias que sostienen el plan/i })).queryByRole("button", { name: /2000001.*modelos estadísticos/i })).not.toBeInTheDocument();
  });

  it("supports component lanes and passes automated accessibility checks", async () => {
    const { container } = render(<CurriculumMapPage map={fixture as CurriculumMap} />);

    fireEvent.change(screen.getByLabelText("Vista de exploración"), { target: { value: "component-lanes" } });
    expect(screen.getByRole("heading", { name: "Fundamentación" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Núcleo estadístico" })).toBeInTheDocument();
    expect(screen.getAllByText(/cálculo diferencial/i).length).toBeGreaterThan(0);

    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it("does not present unavailable planner layouts as real routes or semesters", () => {
    render(<CurriculumMapPage map={fixture as CurriculumMap} />);

    fireEvent.change(screen.getByLabelText("Vista de exploración"), { target: { value: "suggested-path" } });
    expect(screen.getByText(/ruta sugerida pendiente de planificación/i)).toBeInTheDocument();
    expect(screen.getByText(/no es una recomendación de cursado/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Vista de exploración"), { target: { value: "user-scenario" } });
    expect(screen.getByText(/escenario personal no seleccionado/i)).toBeInTheDocument();
    expect(screen.getByText(/hasta que exista un escenario explícito/i)).toBeInTheDocument();
  });
});
