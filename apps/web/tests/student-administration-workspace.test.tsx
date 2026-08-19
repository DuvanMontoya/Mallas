import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudentAdministrationWorkspace } from "../components/student-administration-workspace";
import type { AdminEnrollment, AdminEnrollmentPage, StudentAdminCatalog } from "../lib/api";

const { confirmAdminEnrollmentRevision, createAdminEnrollment, createAdminEnrollmentTransition, getAdminEnrollmentIdentity, getAdminEnrollments, overrideAdminEnrollmentAssignment, previewAdminCurriculumAssignment, previewAdminEnrollmentTransition, updateAdminEnrollmentIdentity } = vi.hoisted(() => ({
  confirmAdminEnrollmentRevision: vi.fn(),
  createAdminEnrollment: vi.fn(),
  createAdminEnrollmentTransition: vi.fn(),
  getAdminEnrollments: vi.fn(),
  getAdminEnrollmentIdentity: vi.fn(),
  overrideAdminEnrollmentAssignment: vi.fn(),
  previewAdminCurriculumAssignment: vi.fn(),
  previewAdminEnrollmentTransition: vi.fn(),
  updateAdminEnrollmentIdentity: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, confirmAdminEnrollmentRevision, createAdminEnrollment, createAdminEnrollmentTransition, getAdminEnrollmentIdentity, getAdminEnrollments, overrideAdminEnrollmentAssignment, previewAdminCurriculumAssignment, previewAdminEnrollmentTransition, updateAdminEnrollmentIdentity };
});

const catalog: StudentAdminCatalog = {
  institutions: [{ id: "inst-1", name: "Universidad Nacional" }],
  programs: [{ id: "program-1", institution_id: "inst-1", campus_id: "campus-1", campus_name: "Bogotá", code: "STAT", name: "Estadística" }],
  plans: [{ id: "plan-1", program_id: "program-1", code: "2514", title: "Plan de Estadística" }],
  revisions: [{ id: "revision-1", plan_id: "plan-1", code: "2514-2023", status: "PUBLISHED", effective_from: "2023-01-01", effective_to: null }],
  terms: [{ id: "term-1", institution_id: "inst-1", campus_id: "campus-1", code: "2026-1S", status: "OPEN", starts_at: "2026-01-01T00:00:00Z", ends_at: "2026-06-30T00:00:00Z", admission_source_status: "VERIFIED" }],
};

const enrollment: AdminEnrollment = {
  id: "enrollment-1",
  student_profile_id: "student-1",
  email: "actual@unal.edu.co",
  display_name: "Estudiante Actual",
  first_name: "Estudiante",
  middle_names: "",
  first_surname: "Actual",
  second_surname: "",
  preferred_name: "",
  birth_date: "2004-08-19",
  age: 22,
  identity_data_status: "CONFIRMED",
  identity_verification_method: "INSTITUTION_VERIFIED",
  identity_version: "2026-08-17T12:00:00+00:00",
  student_number: "10001",
  institution_id: "inst-1",
  program_id: "program-1",
  program_name: "Estadística",
  plan_id: "plan-1",
  plan_code: "2514",
  revision_basis_id: "revision-1",
  admission_term_id: "term-1",
  admission_term_code: "2026-1S",
  status: "ACTIVE",
  cohort_code: "2026-1S",
  review_reasons: [],
  version: "2026-08-17T12:00:00+00:00",
};

describe("StudentAdministrationWorkspace", () => {
  beforeEach(() => {
    createAdminEnrollment.mockReset();
    confirmAdminEnrollmentRevision.mockReset();
    getAdminEnrollments.mockReset();
    getAdminEnrollmentIdentity.mockReset();
    previewAdminCurriculumAssignment.mockReset();
    updateAdminEnrollmentIdentity.mockReset();
    previewAdminCurriculumAssignment.mockResolvedValue({
      data: {
        resolver_version: "1.0.0",
        input: { program_id: "program-1", admission_date: "2026-01-01", context: "ADMISSION", cohort_code: "", previous_plan_id: null, admission_source_snapshot_id: "snapshot-1", admission_source_sha256: "b".repeat(64), admission_verification_method: "SOURCE_SNAPSHOT", admission_record_reference_hash: null },
        status: "RESOLVED",
        reason_codes: ["EXACT_VERIFIED_POLICY"],
        candidates: [],
        selected_policy_id: "policy-1",
        selected_plan_id: "plan-1",
        selected_revision_id: "revision-1",
        decision_hash: "a".repeat(64),
        admission_term_id: "term-1",
        admission_term_code: "2026-1S",
        admission_term_source_status: "VERIFIED",
        selected_plan_code: "2514",
        selected_revision_code: "2514-2023",
      },
      failure: null,
    });
  });

  it("filters existing enrollments and creates account plus enrollment with the scoped catalog", async () => {
    createAdminEnrollment.mockResolvedValue({
      data: { ...enrollment, id: "enrollment-2", email: "nueva@unal.edu.co", display_name: "Nueva Estudiante", student_number: "10002" },
      failure: null,
    });
    const initialPage: AdminEnrollmentPage = { items: [enrollment], total: 51, limit: 50, offset: 0, next_offset: 50, previous_offset: null };
    getAdminEnrollments.mockImplementation(({ search, offset }: { search?: string; offset?: number }) => Promise.resolve({
      data: search ? { ...initialPage, items: [], total: 0, next_offset: null } : { ...initialPage, items: [{ ...enrollment, id: "enrollment-2", email: "nueva@unal.edu.co", display_name: "Nueva Estudiante", student_number: "10002" }, enrollment], total: 52, offset: offset ?? 0 },
      failure: null,
    }));
    const { container } = render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} />);
    expect(await screen.findByText(/Asignación automática verificada/)).toBeInTheDocument();
    expect((await axe.run(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() => expect(getAdminEnrollments).toHaveBeenCalledWith(expect.objectContaining({ offset: 50 })));

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar" }), { target: { value: "sin coincidencia" } });
    expect(await screen.findByText("No hay matrículas que coincidan con la búsqueda.")).toBeInTheDocument();
    expect(getAdminEnrollments).toHaveBeenCalledWith(expect.objectContaining({ search: "sin coincidencia", offset: 0 }));

    fireEvent.change(screen.getByLabelText("Primer nombre"), { target: { value: "Nueva" } });
    fireEvent.change(screen.getByLabelText("Otros nombres (opcional)"), { target: { value: "María" } });
    fireEvent.change(screen.getByLabelText("Primer apellido"), { target: { value: "Estudiante" } });
    fireEvent.change(screen.getByLabelText("Segundo apellido (opcional)"), { target: { value: "Ejemplo" } });
    fireEvent.change(screen.getByLabelText(/Nombre preferido/), { target: { value: "Nue" } });
    fireEvent.change(screen.getByLabelText(/Fecha de nacimiento/), { target: { value: "2004-08-19" } });
    fireEvent.change(screen.getByLabelText("Correo de acceso"), { target: { value: "nueva@unal.edu.co" } });
    fireEvent.change(screen.getByLabelText("Número estudiantil"), { target: { value: "10002" } });
    fireEvent.change(screen.getByLabelText(/Contraseña temporal/), { target: { value: "SafeEnrollment!2026-Xp4" } });
    fireEvent.change(screen.getByLabelText(/Referencia institucional de admisión/), { target: { value: "SIA-ADM-2026-001" } });
    await waitFor(() => expect(previewAdminCurriculumAssignment).toHaveBeenLastCalledWith(expect.objectContaining({ admission_record_reference: "SIA-ADM-2026-001" })));
    fireEvent.click(screen.getByRole("button", { name: "Crear cuenta y matrícula" }));

    await waitFor(() => expect(createAdminEnrollment).toHaveBeenCalledWith(expect.objectContaining({
      email: "nueva@unal.edu.co",
      first_name: "Nueva",
      middle_names: "María",
      first_surname: "Estudiante",
      second_surname: "Ejemplo",
      preferred_name: "Nue",
      birth_date: "2004-08-19",
      institution_id: "inst-1",
      program_id: "program-1",
      admission_term_id: "term-1",
      assignment_context: "ADMISSION",
      expected_assignment_hash: "a".repeat(64),
      admission_verification_method: "SOURCE_SNAPSHOT",
      admission_record_reference: "SIA-ADM-2026-001",
    })));
    expect(await screen.findByText("Cuenta y matrícula creadas para Nueva Estudiante.")).toBeInTheDocument();
    expect(screen.getAllByText("Nueva Estudiante").length).toBeGreaterThanOrEqual(1);
  });

  it("lets an administrator reevaluate a pending enrollment without choosing a plan", async () => {
    const needsReview = { ...enrollment, status: "NEEDS_REVIEW", review_reasons: ["CURRICULUM_ASSIGNMENT"] };
    confirmAdminEnrollmentRevision.mockResolvedValue({
      data: { ...needsReview, status: "ACTIVE", version: "2026-08-17T12:01:00+00:00" },
      failure: null,
    });
    const initialPage: AdminEnrollmentPage = { items: [needsReview], total: 1, limit: 50, offset: 0, next_offset: null, previous_offset: null };
    render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} />);

    fireEvent.click(screen.getByText("Reevaluar asignación curricular"));
    fireEvent.click(screen.getByRole("button", { name: "Reevaluar política" }));

    await waitFor(() => expect(confirmAdminEnrollmentRevision).toHaveBeenCalledWith(
      "enrollment-1",
      {},
      "2026-08-17T12:00:00+00:00",
    ));
    expect(await screen.findByText("Asignación curricular verificada para Estudiante Actual.")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
  });

  it("rectifies structured identity using its independent version", async () => {
    getAdminEnrollmentIdentity.mockResolvedValue({ data: enrollment, failure: null });
    updateAdminEnrollmentIdentity.mockResolvedValue({
      data: { ...enrollment, display_name: "Ana María López Ruiz", first_name: "Ana", middle_names: "María", first_surname: "López", second_surname: "Ruiz", identity_version: "2026-08-17T12:02:00+00:00" },
      failure: null,
    });
    const second = { ...enrollment, id: "enrollment-2", display_name: "Otra Persona", student_number: "10002" };
    const initialPage: AdminEnrollmentPage = { items: [enrollment, second], total: 2, limit: 50, offset: 0, next_offset: null, previous_offset: null };
    const { container } = render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} />);

    const summary = screen.getByText("Revisar identidad de Estudiante Actual");
    expect(screen.getByText("Revisar identidad de Otra Persona")).toBeInTheDocument();
    fireEvent.click(summary);
    const identityForm = within(summary.closest("details") as HTMLElement);
    expect(await identityForm.findByText(/Identidad de Estudiante Actual/)).toBeInTheDocument();
    fireEvent.change(identityForm.getByLabelText("Primer nombre de Estudiante Actual"), { target: { value: "Ana" } });
    fireEvent.change(identityForm.getByLabelText("Otros nombres de Estudiante Actual"), { target: { value: "María" } });
    fireEvent.change(identityForm.getByLabelText("Primer apellido de Estudiante Actual"), { target: { value: "López" } });
    fireEvent.change(identityForm.getByLabelText("Segundo apellido de Estudiante Actual"), { target: { value: "Ruiz" } });
    fireEvent.change(identityForm.getByLabelText("Fundamento verificado"), { target: { value: "STUDENT_REQUEST_VERIFIED" } });
    expect((await axe.run(container)).violations).toEqual([]);
    fireEvent.click(identityForm.getByRole("button", { name: "Guardar identidad de Estudiante Actual" }));

    await waitFor(() => expect(updateAdminEnrollmentIdentity).toHaveBeenCalledWith(
      "enrollment-1",
      expect.objectContaining({ first_name: "Ana", first_surname: "López", rationale: "STUDENT_REQUEST_VERIFIED" }),
      enrollment.identity_version,
    ));
    expect(await screen.findByText("Identidad actualizada para Ana María López Ruiz.")).toBeInTheDocument();
    fireEvent.click(summary);
    await waitFor(() => expect(identityForm.queryByLabelText(/Fecha de nacimiento/)).not.toBeInTheDocument());
  });
});
