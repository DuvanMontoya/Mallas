import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import axe from "axe-core";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudentAdministrationWorkspace } from "../components/student-administration-workspace";
import type { AdminEnrollment, AdminEnrollmentPage, StudentAdminCatalog } from "../lib/api";

const { approveAdminOverrideAuthorization, confirmAdminEnrollmentRevision, createAcademicTerm, createAdminEnrollment, createAdminEnrollmentTransition, createAdminOverrideAuthorization, getAdminEnrollmentIdentity, getAdminEnrollments, getAdminOverrideAuthorizations, getAdminOverrideEvidence, getStudentAdminCatalog, overrideAdminEnrollmentAssignment, previewAdminCurriculumAssignment, previewAdminEnrollmentTransition, updateAdminEnrollmentIdentity, verifyAdminAdmissionFact } = vi.hoisted(() => ({
  approveAdminOverrideAuthorization: vi.fn(),
  confirmAdminEnrollmentRevision: vi.fn(),
  createAcademicTerm: vi.fn(),
  createAdminEnrollment: vi.fn(),
  createAdminEnrollmentTransition: vi.fn(),
  createAdminOverrideAuthorization: vi.fn(),
  getAdminEnrollments: vi.fn(),
  getAdminEnrollmentIdentity: vi.fn(),
  getAdminOverrideAuthorizations: vi.fn(),
  getAdminOverrideEvidence: vi.fn(),
  getStudentAdminCatalog: vi.fn(),
  overrideAdminEnrollmentAssignment: vi.fn(),
  previewAdminCurriculumAssignment: vi.fn(),
  previewAdminEnrollmentTransition: vi.fn(),
  updateAdminEnrollmentIdentity: vi.fn(),
  verifyAdminAdmissionFact: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...actual, approveAdminOverrideAuthorization, confirmAdminEnrollmentRevision, createAcademicTerm, createAdminEnrollment, createAdminEnrollmentTransition, createAdminOverrideAuthorization, getAdminEnrollmentIdentity, getAdminEnrollments, getAdminOverrideAuthorizations, getAdminOverrideEvidence, getStudentAdminCatalog, overrideAdminEnrollmentAssignment, previewAdminCurriculumAssignment, previewAdminEnrollmentTransition, updateAdminEnrollmentIdentity, verifyAdminAdmissionFact };
});

const catalog: StudentAdminCatalog = {
  institutions: [{ id: "inst-1", name: "Universidad Nacional" }],
  programs: [{ id: "program-1", institution_id: "inst-1", campus_id: "campus-1", campus_name: "Bogotá", code: "STAT", name: "Estadística" }],
  plans: [{ id: "plan-1", program_id: "program-1", code: "2514", title: "Plan de Estadística" }],
  revisions: [{ id: "revision-1", plan_id: "plan-1", code: "2514-2023", status: "PUBLISHED", effective_from: "2023-01-01", effective_to: null }],
  terms: [{ id: "term-1", institution_id: "inst-1", campus_id: "campus-1", code: "2026-1S", status: "OPEN", starts_at: "2026-01-01T00:00:00Z", ends_at: "2026-06-30T00:00:00Z", admission_source_status: "VERIFIED" }, { id: "term-2", institution_id: "inst-1", campus_id: "campus-1", code: "2026-2S", status: "PLANNED", starts_at: "2026-07-01T00:00:00Z", ends_at: "2026-12-20T00:00:00Z", admission_source_status: "VERIFIED" }],
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
    createAcademicTerm.mockReset();
    getStudentAdminCatalog.mockReset();
    getStudentAdminCatalog.mockResolvedValue({ data: catalog, failure: null });
    createAdminEnrollment.mockReset();
    createAdminEnrollmentTransition.mockReset();
    confirmAdminEnrollmentRevision.mockReset();
    getAdminEnrollments.mockReset();
    getAdminEnrollmentIdentity.mockReset();
    previewAdminCurriculumAssignment.mockReset();
    previewAdminEnrollmentTransition.mockReset();
    updateAdminEnrollmentIdentity.mockReset();
    verifyAdminAdmissionFact.mockReset();
    verifyAdminAdmissionFact.mockResolvedValue({ data: { id: "fact-1", status: "VERIFIED", program_id: "program-1", admission_term_id: "term-1", evidence_id: "admission-evidence-1", content_hash: "f".repeat(64), verified_at: "2026-08-19T01:00:00Z" }, failure: null });
    approveAdminOverrideAuthorization.mockReset();
    createAdminOverrideAuthorization.mockReset();
    getAdminOverrideAuthorizations.mockReset();
    getAdminOverrideEvidence.mockReset();
    getAdminOverrideAuthorizations.mockResolvedValue({ data: [], failure: null });
    getAdminOverrideEvidence.mockResolvedValue({ data: [{ id: "evidence-1", source_title: "Acuerdo verificado", snapshot_sha256: "b".repeat(64), locator: "Artículo 3", excerpt: "Autoriza la excepción individual." }], failure: null });
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
    const { container } = render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} currentUserId={11} />);

    // List toolbar and pagination are modernized but still functional
    expect(await screen.findByRole("button", { name: /Nuevo estudiante/ })).toBeInTheDocument();
    expect((await axe.run(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() => expect(getAdminEnrollments).toHaveBeenCalledWith(expect.objectContaining({ offset: 50 })));

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar" }), { target: { value: "sin coincidencia" } });
    await waitFor(() => expect(screen.getByText("Sin resultados")).toBeInTheDocument());
    expect(getAdminEnrollments).toHaveBeenCalledWith(expect.objectContaining({ search: "sin coincidencia", offset: 0 }));

    // Reset search so list is visible again
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar" }), { target: { value: "" } });
    await waitFor(() => expect(screen.getByText("Estudiante Actual")).toBeInTheDocument());

    // Open wizard (modern professional flow)
    fireEvent.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Contexto académico")).toBeInTheDocument();

    // Context step: verify admission manifest - now intuitive: Código del acta (opcional)
    const referenceInput = within(dialog).getByPlaceholderText(/Ej: RES-2026-1234/);
    fireEvent.change(referenceInput, { target: { value: "SIA-ADM-2026-001" } });
    const verifyBtn = within(dialog).getByRole("button", { name: /Verificar en archivo/ });
    fireEvent.click(verifyBtn);
    await waitFor(() => expect(verifyAdminAdmissionFact).toHaveBeenCalledWith({
      program_id: "program-1",
      admission_term_id: "term-1",
      record_reference: "SIA-ADM-2026-001",
    }));
    expect(await within(dialog).findByRole("button", { name: /Verificada/ })).toBeDisabled();
    await waitFor(() => expect(previewAdminCurriculumAssignment).toHaveBeenCalledWith(expect.objectContaining({ admission_record_reference: "SIA-ADM-2026-001" })));

    // Move to Identity step
    fireEvent.click(within(dialog).getByRole("button", { name: "Continuar" }));
    expect(await within(dialog).findByText("Identidad estructurada")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText(/Primer nombre/), { target: { value: "Nueva" } });
    fireEvent.change(within(dialog).getByLabelText(/Otros nombres/), { target: { value: "María" } });
    fireEvent.change(within(dialog).getByLabelText(/Primer apellido/), { target: { value: "Estudiante" } });
    fireEvent.change(within(dialog).getByLabelText(/Segundo apellido/), { target: { value: "Ejemplo" } });
    fireEvent.change(within(dialog).getByLabelText(/Nombre preferido/), { target: { value: "Nue" } });
    fireEvent.change(within(dialog).getByLabelText(/Fecha de nacimiento/), { target: { value: "2004-08-19" } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Continuar" }));
    expect(await within(dialog).findByText("Credenciales de acceso")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText(/Correo de acceso/), { target: { value: "nueva@unal.edu.co" } });
    fireEvent.change(within(dialog).getByLabelText(/Número estudiantil/), { target: { value: "10002" } });
    fireEvent.change(within(dialog).getByLabelText(/Contraseña temporal/), { target: { value: "SafeEnrollment!2026-Xp4" } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Continuar" }));
    expect(await within(dialog).findByText("Revisión y confirmación")).toBeInTheDocument();
    // assignment preview visible in review
    expect(await within(dialog).findByText(/Asignación automática/)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Crear cuenta y matrícula" }));

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
      admission_verification_method: "VERIFIED_ADMISSION_FACT",
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
    render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} currentUserId={11} />);

    fireEvent.click(screen.getByText("Reevaluar asignación curricular de Estudiante Actual"));
    fireEvent.click(screen.getByRole("button", { name: "Reevaluar política de Estudiante Actual" }));

    await waitFor(() => expect(confirmAdminEnrollmentRevision).toHaveBeenCalledWith(
      "enrollment-1",
      {},
      "2026-08-17T12:00:00+00:00",
    ));
    expect(await screen.findByText("Asignación curricular verificada para Estudiante Actual.")).toBeInTheDocument();
    expect(screen.getAllByText("Activa").length).toBeGreaterThan(0);
  });

  it("prepares, independently approves, and applies a sealed curriculum override", async () => {
    const needsReview = { ...enrollment, plan_id: null, plan_code: null, revision_basis_id: null, status: "NEEDS_REVIEW", review_reasons: ["CURRICULUM_ASSIGNMENT"] };
    const draft = { id: "authorization-1", enrollment_id: enrollment.id, plan_id: "plan-1", plan_code: "2514", revision_basis_id: "revision-1", revision_code: "2514-2023", revision_status: "PUBLISHED", seal_version: "OVERRIDE_AUTH_V2", reason_code: "ADMISSION_POLICY_EXCEPTION", evidence_id: "evidence-1", evidence_source_title: "Acuerdo verificado", evidence_locator: "Artículo 3", evidence_excerpt: "Autoriza la excepción individual.", evidence_snapshot_sha256: "b".repeat(64), evidence_excerpt_hash: "d".repeat(64), status: "DRAFT", prepared_by_id: 10, approved_by_id: null, content_hash: "e".repeat(64), version: "2026-08-19T01:00:00+00:00" };
    createAdminOverrideAuthorization.mockResolvedValue({ data: draft, failure: null });
    approveAdminOverrideAuthorization.mockResolvedValue({ data: { ...draft, status: "APPROVED", approved_by_id: 11, content_hash: "c".repeat(64), version: "2026-08-19T01:01:00+00:00" }, failure: null });
    overrideAdminEnrollmentAssignment.mockResolvedValue({ data: { ...needsReview, plan_id: "plan-1", plan_code: "2514", revision_basis_id: "revision-1", status: "ACTIVE", review_reasons: [], version: "2026-08-19T01:02:00+00:00" }, failure: null });
    render(<StudentAdministrationWorkspace catalog={catalog} initialPage={{ items: [needsReview], total: 1, limit: 50, offset: 0, next_offset: null, previous_offset: null }} currentUserId={11} />);

    fireEvent.click(screen.getByText("Reevaluar asignación curricular de Estudiante Actual"));
    await screen.findByRole("option", { name: /Acuerdo verificado/ });
    fireEvent.click(screen.getByRole("button", { name: "Enviar excepción de Estudiante Actual para aprobación" }));
    expect(await screen.findByText(/Pendiente de segunda aprobación/)).toBeInTheDocument();
    const approve = screen.getByRole("button", { name: "Aprobar excepción de Estudiante Actual como segunda persona" });
    await waitFor(() => expect(approve).toBeEnabled());
    fireEvent.click(approve);
    expect(await screen.findByText(/Aprobada y sellada/)).toBeInTheDocument();
    expect(screen.getByText("Autoriza la excepción individual.")).toBeInTheDocument();
    const apply = screen.getByRole("button", { name: "Aplicar autorización sellada a Estudiante Actual" });
    await waitFor(() => expect(apply).toBeEnabled());
    fireEvent.click(apply);

    await waitFor(() => expect(overrideAdminEnrollmentAssignment).toHaveBeenCalledWith(
      enrollment.id,
      { authorization_id: "authorization-1" },
      enrollment.version,
    ));
    expect(await screen.findByText("Asignación curricular verificada para Estudiante Actual.")).toBeInTheDocument();
  });

  it("rectifies structured identity using its independent version", async () => {
    getAdminEnrollmentIdentity.mockResolvedValue({ data: enrollment, failure: null });
    updateAdminEnrollmentIdentity.mockResolvedValue({
      data: { ...enrollment, display_name: "Ana María López Ruiz", first_name: "Ana", middle_names: "María", first_surname: "López", second_surname: "Ruiz", identity_version: "2026-08-17T12:02:00+00:00" },
      failure: null,
    });
    const second = { ...enrollment, id: "enrollment-2", display_name: "Otra Persona", student_number: "10002" };
    const initialPage: AdminEnrollmentPage = { items: [enrollment, second], total: 2, limit: 50, offset: 0, next_offset: null, previous_offset: null };
    const { container } = render(<StudentAdministrationWorkspace catalog={catalog} initialPage={initialPage} currentUserId={11} />);

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

  it("verifies transition admission and discloses closing the active source", async () => {
    previewAdminEnrollmentTransition.mockResolvedValue({
      data: {
        resolver_version: "1.0.0",
        input: { program_id: "program-1", admission_date: "2026-07-01", context: "PLAN_TRANSITION", cohort_code: "", previous_plan_id: "plan-1", admission_source_snapshot_id: "snapshot-2", admission_source_sha256: "b".repeat(64), admission_verification_method: "VERIFIED_ADMISSION_FACT", admission_record_reference_hash: "h".repeat(64) },
        status: "RESOLVED",
        reason_codes: ["EXACT_VERIFIED_POLICY"],
        candidates: [],
        selected_policy_id: "policy-2",
        selected_plan_id: "plan-1",
        selected_revision_id: "revision-1",
        decision_hash: "t".repeat(64),
        admission_term_id: "term-2",
        admission_term_code: "2026-2S",
        admission_term_source_status: "VERIFIED",
        admission_fact_status: "VERIFIED",
        selected_plan_code: "2514",
        selected_revision_code: "2514-2023",
        source_enrollment_id: enrollment.id,
      },
      failure: null,
    });
    createAdminEnrollmentTransition.mockResolvedValue({ data: { ...enrollment, id: "enrollment-transition", admission_term_id: "term-2", admission_term_code: "2026-2S" }, failure: null });
    render(<StudentAdministrationWorkspace catalog={catalog} initialPage={{ items: [enrollment], total: 1, limit: 50, offset: 0, next_offset: null, previous_offset: null }} currentUserId={11} />);

    fireEvent.click(screen.getByText("Registrar reingreso o transición de Estudiante Actual"));
    fireEvent.change(screen.getByLabelText(/Referencia institucional de la nueva admisión/), { target: { value: "SIA-TRANSITION-001" } });
    fireEvent.click(screen.getByRole("button", { name: "Verificar admisión de Estudiante Actual" }));
    expect(await screen.findByRole("button", { name: "Admisión de Estudiante Actual verificada y sellada" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Evaluar asignación de Estudiante Actual" }));

    expect(await screen.findByText(/cambiará de ACTIVE a TRANSITIONED/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar nueva matrícula de Estudiante Actual" }));
    await waitFor(() => expect(createAdminEnrollmentTransition).toHaveBeenCalledWith(
      enrollment.id,
      expect.objectContaining({
        admission_term_id: "term-2",
        admission_verification_method: "VERIFIED_ADMISSION_FACT",
        admission_record_reference: "SIA-TRANSITION-001",
      }),
    ));
  });

  it("allows creating a period inline when the catalog is empty", async () => {
    const emptyCatalog: StudentAdminCatalog = { ...catalog, terms: [] };
    createAcademicTerm.mockResolvedValue({
      data: {
        id: "term-new",
        code: "2026-1S",
        institution_id: "inst-1",
        campus_code: "Bogotá",
        campus_name: "Bogotá",
        starts_at: "2026-01-12T08:00:00Z",
        ends_at: "2026-06-20T18:00:00Z",
        status: "OPEN",
        source: { sha256: null, retrieved_at: null, freshness: "UNKNOWN", age_seconds: null, max_age_seconds: null, source_name: null, source_url: null, capacity_realtime: false },
      } as any,
      failure: null,
    });
    getStudentAdminCatalog.mockResolvedValue({
      data: {
        ...emptyCatalog,
        terms: [{ id: "term-new", institution_id: "inst-1", campus_id: "campus-1", code: "2026-1S", status: "OPEN", starts_at: "2026-01-12T08:00:00Z", ends_at: "2026-06-20T18:00:00Z", admission_source_status: "UNKNOWN" }],
      } as StudentAdminCatalog,
      failure: null,
    });
    render(<StudentAdministrationWorkspace catalog={emptyCatalog} initialPage={{ items: [], total: 0, limit: 50, offset: 0, next_offset: null, previous_offset: null }} currentUserId={11} />);
    fireEvent.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/No hay períodos de ingreso configurados/)).toBeInTheDocument();
    // creator auto-expanded when empty
    expect(within(dialog).getByLabelText(/Código \*/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: /Crear período 2026-1S/ }));
    await waitFor(() => expect(createAcademicTerm).toHaveBeenCalledWith(expect.objectContaining({ code: "2026-1S", institution_id: "inst-1" })));
    expect(await screen.findByText(/Período 2026-1S creado/)).toBeInTheDocument();
  });
});
