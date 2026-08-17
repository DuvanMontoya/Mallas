import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudentAdministrationWorkspace } from "../components/student-administration-workspace";
import type { AdminEnrollment, StudentAdminCatalog } from "../lib/api";

const { createAdminEnrollment } = vi.hoisted(() => ({ createAdminEnrollment: vi.fn() }));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, createAdminEnrollment };
});

const catalog: StudentAdminCatalog = {
  institutions: [{ id: "inst-1", name: "Universidad Nacional" }],
  programs: [{ id: "program-1", institution_id: "inst-1", campus_id: "campus-1", campus_name: "Bogotá", code: "STAT", name: "Estadística" }],
  plans: [{ id: "plan-1", program_id: "program-1", code: "2514", title: "Plan de Estadística" }],
  revisions: [{ id: "revision-1", plan_id: "plan-1", code: "2514-2023", status: "PUBLISHED" }],
  terms: [{ id: "term-1", institution_id: "inst-1", campus_id: "campus-1", code: "2026-1S", status: "OPEN" }],
};

const enrollment: AdminEnrollment = {
  id: "enrollment-1",
  student_profile_id: "student-1",
  email: "actual@unal.edu.co",
  display_name: "Estudiante Actual",
  student_number: "10001",
  institution_id: "inst-1",
  program_id: "program-1",
  program_name: "Estadística",
  plan_id: "plan-1",
  plan_code: "2514",
  admission_term_id: "term-1",
  admission_term_code: "2026-1S",
  status: "ACTIVE",
  cohort_code: "2026-1S",
};

describe("StudentAdministrationWorkspace", () => {
  beforeEach(() => createAdminEnrollment.mockReset());

  it("filters existing enrollments and creates account plus enrollment with the scoped catalog", async () => {
    createAdminEnrollment.mockResolvedValue({
      data: { ...enrollment, id: "enrollment-2", email: "nueva@unal.edu.co", display_name: "Nueva Estudiante", student_number: "10002" },
      failure: null,
    });
    const { container } = render(<StudentAdministrationWorkspace catalog={catalog} initialEnrollments={[enrollment]} />);
    expect((await axe.run(container)).violations).toEqual([]);

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar" }), { target: { value: "sin coincidencia" } });
    expect(screen.getByText("No hay matrículas que coincidan con la búsqueda.")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar" }), { target: { value: "" } });
    expect(screen.getByText("Estudiante Actual")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: "Nueva Estudiante" } });
    fireEvent.change(screen.getByLabelText("Correo de acceso"), { target: { value: "nueva@unal.edu.co" } });
    fireEvent.change(screen.getByLabelText("Número estudiantil"), { target: { value: "10002" } });
    fireEvent.change(screen.getByLabelText(/Contraseña temporal/), { target: { value: "SafeEnrollment!2026-Xp4" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear cuenta y matrícula" }));

    await waitFor(() => expect(createAdminEnrollment).toHaveBeenCalledWith(expect.objectContaining({
      email: "nueva@unal.edu.co",
      institution_id: "inst-1",
      program_id: "program-1",
      plan_id: "plan-1",
      revision_basis_id: "revision-1",
      admission_term_id: "term-1",
    })));
    expect(await screen.findByText("Cuenta y matrícula creadas para Nueva Estudiante.")).toBeInTheDocument();
    expect(screen.getByText("Nueva Estudiante")).toBeInTheDocument();
  });
});
