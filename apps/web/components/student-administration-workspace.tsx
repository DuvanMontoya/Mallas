"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import {
  confirmAdminEnrollmentRevision,
  createAdminEnrollment,
  createAdminEnrollmentTransition,
  getAdminEnrollmentIdentity,
  getAdminEnrollments,
  overrideAdminEnrollmentAssignment,
  previewAdminCurriculumAssignment,
  previewAdminEnrollmentTransition,
  updateAdminEnrollmentIdentity,
  type AdminEnrollment,
  type AdminEnrollmentSummary,
  type AdminEnrollmentCreatePayload,
  type AdminEnrollmentPage,
  type AdminAssignmentPreview,
  type StudentAdminCatalog,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

function firstId<T extends { id: string }>(items: T[]) {
  return items[0]?.id ?? "";
}

function toEnrollmentSummary(value: AdminEnrollment): AdminEnrollmentSummary {
  return {
    id: value.id,
    student_profile_id: value.student_profile_id,
    email: value.email,
    display_name: value.display_name,
    identity_data_status: value.identity_data_status,
    student_number: value.student_number,
    institution_id: value.institution_id,
    program_id: value.program_id,
    program_name: value.program_name,
    plan_id: value.plan_id,
    plan_code: value.plan_code,
    revision_basis_id: value.revision_basis_id,
    admission_term_id: value.admission_term_id,
    admission_term_code: value.admission_term_code,
    status: value.status,
    cohort_code: value.cohort_code,
    review_reasons: value.review_reasons,
    version: value.version,
  };
}

function EnrollmentResolution({ enrollment, catalog, onResolved }: { enrollment: AdminEnrollmentSummary; catalog: StudentAdminCatalog; onResolved: (value: AdminEnrollmentSummary) => void }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const admissionTerm = catalog.terms.find((term) => term.id === enrollment.admission_term_id);
  const plans = catalog.plans.filter((plan) => plan.program_id === enrollment.program_id);
  const revisions = catalog.revisions.filter((revision) =>
    plans.some((plan) => plan.id === revision.plan_id),
  );
  return (
    <details className="student-admin-resolution">
      <summary>Reevaluar asignación curricular</summary>
      <div>
        <p className="student-admin-resolution-context"><strong>Ingreso {enrollment.admission_term_code}</strong>{admissionTerm ? ` · ${admissionTerm.starts_at.slice(0, 10)}` : ""}<span>El sistema volverá a evaluar exclusivamente políticas publicadas y verificadas. No permite escoger un plan manualmente.</span></p>
        {error ? <Alert tone="error">{error}</Alert> : null}
        <button
          className="button button-primary"
          type="button"
          disabled={pending}
          onClick={() => startTransition(async () => {
            setError(null);
            const result = await confirmAdminEnrollmentRevision(
              enrollment.id,
              {},
              enrollment.version,
            );
            if (!result.data) {
              setError(result.failure?.problem?.detail ?? "Todavía no existe una política verificable para activar esta matrícula.");
              return;
            }
            onResolved(result.data);
          })}
        >
          {pending ? "Reevaluando…" : "Reevaluar política"}
        </button>
      </div>
      <form className="student-admin-governed-override" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        startTransition(async () => {
          setError(null);
          const result = await overrideAdminEnrollmentAssignment(
            enrollment.id,
            {
              plan_id: String(form.get("override_plan_id") ?? ""),
              revision_basis_id: String(form.get("override_revision_id") ?? ""),
              evidence_id: String(form.get("override_evidence_id") ?? ""),
              exception_id: String(form.get("override_exception_id") ?? ""),
              reason_code: String(form.get("override_reason_code") ?? ""),
            },
            enrollment.version,
          );
          if (!result.data) {
            setError(result.failure?.problem?.detail ?? "La autorización no permite esta excepción curricular.");
            return;
          }
          onResolved(result.data);
        });
      }}>
        <fieldset>
          <legend>Excepción institucional aprobada</legend>
          <p className="student-admin-resolution-context"><span>Use esta vía únicamente cuando exista una excepción aprobada, vigente y evidenciada para esta matrícula. El servidor comprobará que autorice exactamente el plan, la revisión y el motivo.</span></p>
          <label className="field-group"><span>Plan autorizado</span><select name="override_plan_id" required>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.code} · {plan.title}</option>)}</select></label>
          <label className="field-group"><span>Revisión autorizada</span><select name="override_revision_id" required>{revisions.map((revision) => <option key={revision.id} value={revision.id}>{revision.code} · {revision.status}</option>)}</select></label>
          <label className="field-group"><span>Motivo aprobado</span><select name="override_reason_code" required><option value="ADMISSION_POLICY_EXCEPTION">Excepción a política de admisión</option><option value="REENTRY_INSTITUTIONAL_DECISION">Decisión institucional de reingreso</option><option value="TRANSITION_INSTITUTIONAL_DECISION">Decisión institucional de transición</option><option value="LEGACY_RECORD_VERIFIED">Registro histórico verificado</option></select></label>
          <label className="field-group"><span>ID de la excepción aprobada</span><input name="override_exception_id" required aria-describedby={`override-help-${enrollment.id}`} /></label>
          <label className="field-group"><span>ID de la evidencia vinculada</span><input name="override_evidence_id" required aria-describedby={`override-help-${enrollment.id}`} /></label>
          <small id={`override-help-${enrollment.id}`}>Ambos identificadores provienen del expediente de gobernanza; no convierten texto libre en una autorización.</small>
          <button className="button button-secondary" type="submit" disabled={pending}>{pending ? "Verificando excepción…" : "Aplicar excepción aprobada"}</button>
        </fieldset>
      </form>
    </details>
  );
}

function EnrollmentTransition({ enrollment, catalog, onCreated }: { enrollment: AdminEnrollmentSummary; catalog: StudentAdminCatalog; onCreated: (value: AdminEnrollmentSummary) => void }) {
  const program = catalog.programs.find((item) => item.id === enrollment.program_id);
  const terms = catalog.terms.filter((term) => term.institution_id === enrollment.institution_id && (!term.campus_id || term.campus_id === program?.campus_id) && term.id !== enrollment.admission_term_id);
  const [preview, setPreview] = useState<AdminAssignmentPreview | null>(null);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  return (
    <details className="student-admin-resolution">
      <summary>Registrar reingreso o transición de {enrollment.display_name || enrollment.student_number}</summary>
      <form onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const payload = {
          admission_term_id: String(form.get("transition_term_id") ?? ""),
          context: String(form.get("transition_context") ?? "REENTRY"),
          cohort_code: String(form.get("transition_cohort") ?? ""),
          admission_verification_method: "SOURCE_SNAPSHOT",
          admission_record_reference: String(form.get("transition_reference") ?? "") || null,
        };
        startTransition(async () => {
          setError(null);
          if (!preview) {
            const result = await previewAdminEnrollmentTransition(enrollment.id, payload);
            if (!result.data) {
              setError(result.failure?.problem?.detail ?? "No fue posible evaluar el reingreso o transición.");
              return;
            }
            setPreview(result.data);
            return;
          }
          const result = await createAdminEnrollmentTransition(enrollment.id, {
            ...payload,
            expected_assignment_hash: preview.decision_hash,
          });
          if (!result.data) {
            setError(result.failure?.problem?.detail ?? "No fue posible registrar la nueva matrícula.");
            return;
          }
          setPreview(null);
          onCreated(result.data);
        });
      }} onChange={() => setPreview(null)}>
        <fieldset>
          <legend>Nueva vinculación del mismo estudiante</legend>
          <p className="student-admin-resolution-context"><span>El plan anterior se deriva de esta matrícula; no se escribe manualmente. Una política publicada debe resolver el nuevo plan o la nueva matrícula quedará en revisión.</span></p>
          <label className="field-group"><span>Contexto</span><select name="transition_context"><option value="REENTRY">Reingreso</option><option value="PLAN_TRANSITION">Transición de plan</option></select></label>
          <label className="field-group"><span>Nuevo período</span><select name="transition_term_id" required>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · fuente {term.admission_source_status === "VERIFIED" ? "verificada" : "pendiente"}</option>)}</select></label>
          <label className="field-group"><span>Cohorte (opcional)</span><input name="transition_cohort" /></label>
          <label className="field-group"><span>Referencia institucional (seguimiento opcional)</span><input name="transition_reference" /></label>
          {preview ? preview.status === "RESOLVED" ? <Alert tone="success">Plan {preview.selected_plan_code}, revisión {preview.selected_revision_code}. Confirma para crear la matrícula.</Alert> : <Alert tone="warning">La nueva matrícula quedará en revisión: {preview.reason_codes.join(", ")}.</Alert> : null}
          {error ? <Alert tone="error">{error}</Alert> : null}
          <button className="button button-secondary" type="submit" disabled={pending || terms.length === 0}>{pending ? "Procesando…" : preview ? "Confirmar nueva matrícula" : "Evaluar asignación"}</button>
        </fieldset>
      </form>
    </details>
  );
}

function IdentityRectification({ enrollment, onUpdated }: { enrollment: AdminEnrollmentSummary; onUpdated: (value: AdminEnrollmentSummary) => void }) {
  const [identity, setIdentity] = useState<AdminEnrollment | null>(null);
  const identityRequestSequence = useRef(0);
  const [loading, setLoading] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const label = enrollment.display_name || enrollment.student_number || enrollment.email;
  const legendId = `identity-legend-${enrollment.id}`;
  const errorId = `identity-error-${enrollment.id}`;

  async function loadIdentity() {
    if (identity || loading) return;
    const sequence = ++identityRequestSequence.current;
    setLoading(true);
    setError(null);
    const result = await getAdminEnrollmentIdentity(enrollment.id);
    if (sequence !== identityRequestSequence.current) return;
    setLoading(false);
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "No fue posible cargar la identidad privada.");
      return;
    }
    setIdentity(result.data);
  }

  return (
    <details className="student-admin-resolution" onToggle={(event) => {
      if (event.currentTarget.open) void loadIdentity();
      else {
        identityRequestSequence.current += 1;
        setIdentity(null);
        setLoading(false);
        setError(null);
      }
    }}>
      <summary>Revisar identidad de {label}</summary>
      {loading ? <p role="status">Cargando identidad privada…</p> : null}
      {identity ? <form key={identity.identity_version} aria-labelledby={legendId} aria-describedby={error ? errorId : undefined} onSubmit={(event) => {
        event.preventDefault();
        setError(null);
        const form = new FormData(event.currentTarget);
        startTransition(async () => {
          const result = await updateAdminEnrollmentIdentity(
            enrollment.id,
            {
              first_name: String(form.get("first_name") ?? ""),
              middle_names: String(form.get("middle_names") ?? ""),
              first_surname: String(form.get("first_surname") ?? ""),
              second_surname: String(form.get("second_surname") ?? ""),
              preferred_name: String(form.get("preferred_name") ?? ""),
              birth_date: String(form.get("birth_date") ?? ""),
              rationale: String(form.get("rationale") ?? "OTHER_VERIFIED"),
            },
            identity.identity_version,
          );
          if (!result.data) {
            setError(result.failure?.problem?.detail ?? "No fue posible rectificar la identidad.");
            return;
          }
          setIdentity(result.data);
          onUpdated(toEnrollmentSummary(result.data));
        });
      }}>
        <fieldset>
          <legend id={legendId}>Identidad de {label} · {enrollment.student_number}</legend>
          <p className="student-admin-resolution-context"><span>La rectificación queda auditada sin copiar nombres ni fecha de nacimiento al evento.</span></p>
          <label className="field-group"><span>Primer nombre de {label}</span><input name="first_name" defaultValue={identity.first_name} required /></label>
          <label className="field-group"><span>Otros nombres de {label}</span><input name="middle_names" defaultValue={identity.middle_names} /></label>
          <label className="field-group"><span>Primer apellido de {label}</span><input name="first_surname" defaultValue={identity.first_surname} required /></label>
          <label className="field-group"><span>Segundo apellido de {label}</span><input name="second_surname" defaultValue={identity.second_surname} /></label>
          <label className="field-group"><span>Nombre preferido de {label}</span><input name="preferred_name" defaultValue={identity.preferred_name} /></label>
          <label className="field-group"><span>Fecha de nacimiento de {label}</span><input name="birth_date" type="date" defaultValue={identity.birth_date ?? ""} required /></label>
          <label className="field-group"><span>Fundamento verificado</span><select name="rationale" defaultValue="STUDENT_REQUEST_VERIFIED"><option value="STUDENT_REQUEST_VERIFIED">Solicitud de la persona verificada</option><option value="AUTHORIZED_SOURCE_VERIFIED">Fuente institucional autorizada</option><option value="DATA_ENTRY_CORRECTION">Corrección de digitación comprobada</option><option value="OTHER_VERIFIED">Otro fundamento verificado</option></select></label>
          {error ? <div id={errorId}><Alert tone="error">{error}</Alert></div> : null}
          <button className="button button-primary" type="submit" disabled={pending}>{pending ? `Guardando identidad de ${label}…` : `Guardar identidad de ${label}`}</button>
        </fieldset>
      </form> : null}
      {!loading && !identity && error ? <div id={errorId}><Alert tone="error">{error}</Alert></div> : null}
    </details>
  );
}

export function StudentAdministrationWorkspace({
  catalog,
  initialPage,
}: {
  catalog: StudentAdminCatalog;
  initialPage: AdminEnrollmentPage;
}) {
  const [enrollments, setEnrollments] = useState(initialPage.items);
  const [total, setTotal] = useState(initialPage.total);
  const [page, setPage] = useState(initialPage);
  const [search, setSearch] = useState("");
  const [searching, setSearching] = useState(false);
  const initialSearchRender = useRef(true);
  const searchRequestSequence = useRef(0);
  const [institutionId, setInstitutionId] = useState(firstId(catalog.institutions));
  const programs = useMemo(
    () => catalog.programs.filter((program) => program.institution_id === institutionId),
    [catalog.programs, institutionId],
  );
  const [programId, setProgramId] = useState(firstId(programs));
  const activeProgram = programs.find((program) => program.id === programId) ?? programs[0];
  const terms = catalog.terms.filter(
    (term) => term.institution_id === institutionId && (!term.campus_id || term.campus_id === activeProgram?.campus_id),
  );
  const [termId, setTermId] = useState(firstId(terms));
  const selectedTerm = terms.find((term) => term.id === termId) ?? terms[0];
  const [cohortCode, setCohortCode] = useState("");
  const [admissionReference, setAdmissionReference] = useState("");
  const [assignment, setAssignment] = useState<AdminAssignmentPreview | null>(null);
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const assignmentRequestSequence = useRef(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  async function loadEnrollments(nextOffset: number, nextSearch = search) {
    const sequence = ++searchRequestSequence.current;
    setSearching(true);
    setError(null);
    const result = await getAdminEnrollments({
      search: nextSearch.trim() || undefined,
      limit: initialPage.limit,
      offset: nextOffset,
    });
    if (sequence !== searchRequestSequence.current) return;
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "No fue posible consultar las matrículas.");
      setSearching(false);
      return;
    }
    setEnrollments(result.data.items);
    setTotal(result.data.total);
    setPage(result.data);
    setSearching(false);
  }

  useEffect(() => {
    if (initialSearchRender.current) {
      initialSearchRender.current = false;
      return;
    }
    const timeout = window.setTimeout(() => void loadEnrollments(0, search), 300);
    return () => window.clearTimeout(timeout);
    // loadEnrollments is intentionally driven only by the remote search term.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  useEffect(() => {
    if (!activeProgram?.id || !selectedTerm?.id) {
      setAssignment(null);
      return;
    }
    const sequence = ++assignmentRequestSequence.current;
    setAssignmentLoading(true);
    const timeout = window.setTimeout(async () => {
      const result = await previewAdminCurriculumAssignment({
        program_id: activeProgram.id,
        admission_term_id: selectedTerm.id,
        context: "ADMISSION",
        cohort_code: cohortCode.trim(),
        admission_verification_method: "SOURCE_SNAPSHOT",
        admission_record_reference: admissionReference.trim() || null,
      });
      if (sequence !== assignmentRequestSequence.current) return;
      setAssignmentLoading(false);
      if (!result.data) {
        setAssignment(null);
        setError(result.failure?.problem?.detail ?? "No fue posible resolver la asignación curricular.");
        return;
      }
      setAssignment(result.data);
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [activeProgram?.id, admissionReference, cohortCode, selectedTerm?.id]);

  function chooseInstitution(nextInstitutionId: string) {
    setInstitutionId(nextInstitutionId);
    const nextPrograms = catalog.programs.filter(
      (program) => program.institution_id === nextInstitutionId,
    );
    const nextProgram = nextPrograms[0];
    setProgramId(nextProgram?.id ?? "");
    setTermId(catalog.terms.find((term) => term.institution_id === nextInstitutionId && (!term.campus_id || term.campus_id === nextProgram?.campus_id))?.id ?? "");
  }

  function chooseProgram(nextProgramId: string) {
    setProgramId(nextProgramId);
    const nextProgram = catalog.programs.find((program) => program.id === nextProgramId);
    setTermId(catalog.terms.find((term) => term.institution_id === nextProgram?.institution_id && (!term.campus_id || term.campus_id === nextProgram?.campus_id))?.id ?? "");
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    if (!institutionId || !activeProgram || !selectedTerm) {
      setError("Completa el programa y el período de ingreso.");
      return;
    }
    if (!assignment) {
      setError("Espera a que termine la evaluación de la política curricular.");
      return;
    }
    const payload: AdminEnrollmentCreatePayload = {
      email: String(form.get("email") ?? ""),
      temporary_password: String(form.get("temporary_password") ?? ""),
      first_name: String(form.get("first_name") ?? ""),
      middle_names: String(form.get("middle_names") ?? ""),
      first_surname: String(form.get("first_surname") ?? ""),
      second_surname: String(form.get("second_surname") ?? ""),
      preferred_name: String(form.get("preferred_name") ?? ""),
      birth_date: String(form.get("birth_date") ?? ""),
      student_number: String(form.get("student_number") ?? ""),
      cohort_code: cohortCode.trim(),
      institution_id: institutionId,
      program_id: activeProgram.id,
      admission_term_id: selectedTerm.id,
      assignment_context: "ADMISSION",
      expected_assignment_hash: assignment.decision_hash,
      admission_verification_method: "SOURCE_SNAPSHOT",
      admission_record_reference: admissionReference.trim(),
    };
    const formElement = event.currentTarget;
    startTransition(async () => {
      const result = await createAdminEnrollment(payload);
      if (!result.data) {
        setError(result.failure?.problem?.detail ?? "No fue posible crear la cuenta y la matrícula.");
        return;
      }
      setSearch("");
      await loadEnrollments(0, "");
      setMessage(result.data.status === "ACTIVE" ? `Cuenta y matrícula creadas para ${result.data.display_name}.` : `Cuenta creada para ${result.data.display_name}; la matrícula quedó pendiente de política curricular verificada.`);
      formElement.reset();
      setCohortCode("");
      setAdmissionReference("");
    });
  }

  const termStatus = (status: string) => ({ OPEN: "Abierto", PLANNED: "Planeado", CLOSED: "Cerrado", COMPLETED: "Finalizado" })[status] ?? "Estado no reconocido";
  const enrollmentStatus = (status: string) => ({ ACTIVE: "Activa", COMPLETED: "Finalizada", WITHDRAWN: "Retirada", SUSPENDED: "Suspendida", NEEDS_REVIEW: "Requiere revisión" })[status] ?? "Estado no reconocido";

  return (
    <div className="student-admin-workspace">
      <header className="route-command student-admin-command">
        <div><p className="eyebrow accent">Administración académica</p><h1>Estudiantes y matrículas</h1></div>
        <label className="command-search"><span>Buscar</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nombre, correo o número" /></label>
      </header>
      {message ? <Alert tone="success">{message}</Alert> : null}
      {error ? <Alert tone="error">{error}</Alert> : null}
      <div className="student-admin-layout">
        <section className="panel student-admin-list" aria-labelledby="managed-students-title">
          <div className="section-heading"><div><p className="eyebrow">Matrículas activas y registradas</p><h2 id="managed-students-title">{total} estudiantes</h2></div></div>
          {searching ? <p className="empty-copy" role="status">Buscando matrículas…</p> : enrollments.length ? <div className="student-admin-rows">{enrollments.map((enrollment) => <article key={enrollment.id}><div><strong>{enrollment.display_name || enrollment.email}</strong><span>{enrollment.student_number || "Sin número"} · {enrollment.email}</span></div><div><span>{enrollment.program_name}</span><small>{enrollment.plan_code ? `Plan ${enrollment.plan_code}` : "Plan pendiente de verificación"} · ingreso {enrollment.admission_term_code}</small></div><StatusBadge tone={enrollment.status === "ACTIVE" ? "eligible" : "unknown"} label={enrollmentStatus(enrollment.status)} /><IdentityRectification enrollment={enrollment} onUpdated={(updated) => { setEnrollments((current) => current.map((item) => item.id === updated.id ? updated : item)); setMessage(`Identidad actualizada para ${updated.display_name}.`); }} />{enrollment.status === "NEEDS_REVIEW" && enrollment.review_reasons.includes("CURRICULUM_ASSIGNMENT") ? <EnrollmentResolution enrollment={enrollment} catalog={catalog} onResolved={(updated) => { setEnrollments((current) => current.map((item) => item.id === updated.id ? updated : item)); setMessage(`Asignación curricular verificada para ${updated.display_name}.`); }} /> : null}{enrollment.plan_id ? <EnrollmentTransition enrollment={enrollment} catalog={catalog} onCreated={(created) => { setEnrollments((current) => [created, ...current]); setTotal((current) => current + 1); setMessage(`Nueva matrícula registrada para ${created.display_name}.`); }} /> : null}</article>)}</div> : <p className="empty-copy">No hay matrículas que coincidan con la búsqueda.</p>}
          <nav className="pagination-controls" aria-label="Páginas de matrículas"><button type="button" className="button button-secondary" disabled={searching || page.previous_offset === null} onClick={() => void loadEnrollments(page.previous_offset ?? 0)}>Anterior</button><span>Página {Math.floor(page.offset / page.limit) + 1} de {Math.max(1, Math.ceil(total / page.limit))}</span><button type="button" className="button button-secondary" disabled={searching || page.next_offset === null} onClick={() => void loadEnrollments(page.next_offset ?? 0)}>Siguiente</button></nav>
        </section>

        <section className="panel student-admin-create" aria-labelledby="create-student-title">
          <div className="section-heading"><div><p className="eyebrow">Alta completa</p><h2 id="create-student-title">Crear estudiante</h2></div></div>
          <form onSubmit={submit} className="student-admin-form">
            <fieldset><legend>Identidad y acceso</legend><label className="field-group"><span>Primer nombre</span><input name="first_name" required autoComplete="given-name" /></label><label className="field-group"><span>Otros nombres (opcional)</span><input name="middle_names" autoComplete="additional-name" /></label><label className="field-group"><span>Primer apellido</span><input name="first_surname" required autoComplete="family-name" /></label><label className="field-group"><span>Segundo apellido (opcional)</span><input name="second_surname" /></label><label className="field-group"><span>Nombre preferido (opcional)</span><input name="preferred_name" /><small>No reemplaza el nombre académico; se usa sólo para trato personal.</small></label><label className="field-group"><span>Fecha de nacimiento</span><input name="birth_date" type="date" required autoComplete="bday" /><small>La edad se calcula desde esta fecha y no se almacena por separado.</small></label><label className="field-group"><span>Correo de acceso</span><input name="email" type="email" required autoComplete="off" /></label><label className="field-group"><span>Número estudiantil</span><input name="student_number" required /></label><label className="field-group"><span>Contraseña temporal</span><input name="temporary_password" type="password" required minLength={12} autoComplete="new-password" /><small>Compártela por un canal seguro; nunca se guarda ni se vuelve a mostrar en texto claro.</small></label></fieldset>
            <fieldset><legend>Vinculación académica</legend><label className="field-group"><span>Institución</span><select value={institutionId} onChange={(event) => chooseInstitution(event.target.value)} required>{catalog.institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}</select></label><label className="field-group"><span>Programa y sede</span><select value={activeProgram?.id ?? ""} onChange={(event) => chooseProgram(event.target.value)} required>{programs.map((program) => <option key={program.id} value={program.id}>{program.name} · {program.campus_name}</option>)}</select></label><label className="field-group"><span>Período de ingreso</span><select required value={termId} onChange={(event) => setTermId(event.target.value)}>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · {termStatus(term.status)} · fuente {term.admission_source_status === "VERIFIED" ? "verificada" : "pendiente"}</option>)}</select></label><label className="field-group"><span>Cohorte (opcional)</span><input name="cohort_code" value={cohortCode} onChange={(event) => setCohortCode(event.target.value)} /></label><label className="field-group"><span>Referencia institucional de admisión (seguimiento opcional)</span><input name="admission_record_reference" value={admissionReference} onChange={(event) => setAdmissionReference(event.target.value)} /><small>Se conserva con HMAC para correlación; escribir una referencia no prueba la admisión ni habilita asignación automática.</small></label><div className="student-admin-assignment" aria-live="polite">{assignmentLoading ? <p>Comprobando política curricular…</p> : assignment?.status === "RESOLVED" ? <Alert tone="success"><strong>Asignación automática verificada:</strong> plan {assignment.selected_plan_code}, revisión {assignment.selected_revision_code}. La decisión conserva política, evidencia y hash reproducible.</Alert> : <Alert tone="warning"><strong>Revisión académica requerida.</strong> No existe una única política publicada y verificada para estos datos. Motivos: {assignment?.reason_codes.join(", ") ?? "sin resolución"}. No se elegirá silenciosamente el primer plan.</Alert>}</div></fieldset>
            <button className="button button-primary" type="submit" disabled={pending || assignmentLoading || !assignment}>{pending ? "Creando…" : assignment?.status === "RESOLVED" ? "Crear cuenta y matrícula" : "Crear cuenta con revisión pendiente"}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
