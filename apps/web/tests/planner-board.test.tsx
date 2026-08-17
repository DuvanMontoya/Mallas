import axe from "axe-core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import scenarioFixture from "./e2e/fixtures/scenarios.json";
import mapFixture from "./e2e/fixtures/curriculum-map.json";
import { PlannerBoard } from "../components/planner-board";
import type { OptimizationRun, PlanningScenario } from "../lib/api";

const mocks = vi.hoisted(() => ({
  updatePlannedCourse: vi.fn(),
  deletePlannedCourse: vi.fn(),
  addPlannedCourse: vi.fn(),
  createScenario: vi.fn(),
  duplicateScenario: vi.fn(),
  archiveScenario: vi.fn(),
  updateScenario: vi.fn(),
  getScenarioCompare: vi.fn(),
  startOptimization: vi.fn(),
  getOptimizationRun: vi.fn(),
  cancelOptimizationRun: vi.fn(),
}));

vi.mock("../lib/api", () => mocks);
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

const scenarios = scenarioFixture.items as PlanningScenario[];
const terms = [
  { id: "00000000-0000-4000-8000-000000000401", code: "2026-2S" },
  { id: "00000000-0000-4000-8000-000000000402", code: "2027-1S" },
];

describe("planner board", () => {
  it("offers a keyboard movement alternative and keeps privacy visible", async () => {
    const updated = structuredClone(scenarios[0]);
    updated.version += 1;
    updated.planned_courses[0].term_id = terms[1].id;
    updated.planned_courses[0].term_code = terms[1].code;
    mocks.updatePlannedCourse.mockResolvedValue({ data: updated, failure: null });

    render(
      <PlannerBoard
        initialScenarios={scenarios}
        initialSelectedId={scenarios[0].id}
        initialCompare={null}
        terms={terms}
        courseOptions={mapFixture.courses}
      />,
    );

    expect(screen.getByRole("heading", { name: scenarios[0].name })).toBeInTheDocument();
    expect(screen.getByText(/borrador privado/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ver mis matriculables/i })).toHaveAttribute("href", "/curriculum?status=ELIGIBLE");
    const moveSelect = screen.getByRole("combobox", { name: /mover 1000003 a otro período/i });
    expect(moveSelect).toHaveValue(terms[0].id);
    fireEvent.change(moveSelect, { target: { value: terms[1].id } });
    await waitFor(() => expect(mocks.updatePlannedCourse).toHaveBeenCalledWith(
      scenarios[0].id,
      scenarios[0].planned_courses[0].id,
      { term_id: terms[1].id },
      { ifMatch: `"${scenarios[0].version}"` },
    ));
    expect(screen.getByRole("button", { name: /bloquear 1000003/i })).toBeInTheDocument();
  });

  it("starts an optimization run and shows the auditable route diff", async () => {
    const run = {
      id: "00000000-0000-4000-8000-000000000701",
      scenario_id: scenarios[0].id,
      input_hash: "input-hash",
      output_hash: "output-hash",
      solver_version: "cp-sat-planner/1.0.0",
      status: "OPTIMAL",
      objective_values: [],
      solution: {
        selected_courses: [
          { course_code: "1000003", term_code: "2027-1S", credits: 4 },
          { course_code: "2000001", term_code: "2026-2S", credits: 4 },
        ],
      },
      explanation: {
        explanations: [{ course_code: "1000003", term_code: "2027-1S" }],
        conflicts: [],
        assumptions: ["UNKNOWN_OFFERINGS_ALLOWED"],
      },
      time_limit_seconds: 30,
      created_at: "2026-08-16T12:00:00Z",
      started_at: "2026-08-16T12:00:00Z",
      cancel_requested_at: null,
      completed_at: "2026-08-16T12:00:01Z",
    } as OptimizationRun;
    mocks.startOptimization.mockResolvedValue({ data: run, failure: null });

    render(
      <PlannerBoard
        initialScenarios={scenarios}
        initialSelectedId={scenarios[0].id}
        initialCompare={null}
        terms={terms}
        courseOptions={mapFixture.courses}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /optimizar ruta/i }));
    await waitFor(() => expect(mocks.startOptimization).toHaveBeenCalledWith(
      scenarios[0].id,
      { time_limit_seconds: 30, unknown_offering_policy: "ALLOW_UNKNOWN", random_seed: 0 },
    ));
    expect((await screen.findAllByText("OPTIMAL")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: /comparación contra el escenario actual/i })).toBeInTheDocument();
    expect(screen.getByText(/2000001 · 2027-1S → 2026-2S/i)).toBeInTheDocument();
    expect(screen.getByText(/unknown_offerings_allowed/i)).toBeInTheDocument();
  });

  it("has no serious automated accessibility violations", async () => {
    const { container } = render(
      <PlannerBoard
        initialScenarios={scenarios}
        initialSelectedId={scenarios[0].id}
        initialCompare={null}
        terms={terms}
        courseOptions={mapFixture.courses}
      />,
    );
    expect((await axe.run(container)).violations).toEqual([]);
  });
});
