import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudentOnboardingForm } from "../components/student-onboarding-form";

const { replace, refresh, updateStudentOnboarding } = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  updateStudentOnboarding: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }) }));
vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, updateStudentOnboarding };
});

const initial = {
  enrollment_id: "enrollment-1",
  program_name: "Estadística",
  program_code: "STAT",
  admission_term_code: "2026-1S",
  enrollment_status: "NEEDS_REVIEW",
  plan_code: null,
  revision_code: null,
  assignment_reason_codes: ["NO_APPLICABLE_POLICY"],
  identity_confirmed: false,
  history_step_status: "PENDING",
  current_term_id: null,
  planning_load_target: null,
  tour_status: "PENDING",
  completed: false,
  version: "2026-08-19T05:00:00Z",
};

const terms = [{
  id: "term-1",
  institution_id: "institution-1",
  campus_code: "BOG",
  campus_name: "Bogotá",
  code: "2026-2S",
  starts_at: "2026-08-01T05:00:00Z",
  ends_at: "2026-12-15T05:00:00Z",
  status: "OPEN",
  source: { sha256: null, retrieved_at: null, freshness: "UNKNOWN", age_seconds: null, max_age_seconds: null, source_name: null, source_url: null, capacity_realtime: false },
}];

describe("StudentOnboardingForm", () => {
  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    updateStudentOnboarding.mockReset();
  });

  it("explains a pending plan and completes the reanudable checklist", async () => {
    updateStudentOnboarding.mockResolvedValue({
      data: { ...initial, identity_confirmed: true, history_step_status: "SKIPPED", current_term_id: "term-1", planning_load_target: 16, tour_status: "COMPLETED", completed: true },
      failure: null,
    });
    const { container } = render(<StudentOnboardingForm initial={initial} terms={terms} />);
    expect(screen.getByText(/Plan pendiente de verificación/)).toBeInTheDocument();
    expect(screen.queryByText(/Plan 2514/)).not.toBeInTheDocument();
    expect((await axe.run(container)).violations).toEqual([]);

    fireEvent.click(screen.getByLabelText("Revisé mis nombres y apellidos"));
    fireEvent.click(screen.getByRole("button", { name: "Terminar y abrir mi espacio" }));

    await waitFor(() => expect(updateStudentOnboarding).toHaveBeenCalledWith(
      expect.objectContaining({
        identity_confirmed: true,
        history_step_status: "SKIPPED",
        current_term_id: "term-1",
        planning_load_target: 16,
        tour_status: "COMPLETED",
        complete: true,
      }),
      initial.version,
    ));
    expect(replace).toHaveBeenCalledWith("/");
  });
});
