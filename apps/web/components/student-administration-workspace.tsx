"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import {
  createAdminEnrollment,
  getAdminEnrollments,
  type AdminEnrollmentCreatePayload,
  type AdminEnrollmentPage,
  type StudentAdminCatalog,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

function firstId<T extends { id: string }>(items: T[]) {
  return items[0]?.id ?? "";
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
  const plans = catalog.plans.filter((plan) => plan.program_id === activeProgram?.id);
  const [planId, setPlanId] = useState(firstId(plans));
  const activePlan = plans.find((plan) => plan.id === planId) ?? plans[0];
  const revisions = catalog.revisions.filter((revision) => revision.plan_id === activePlan?.id);
  const terms = catalog.terms.filter(
    (term) => term.institution_id === institutionId && (!term.campus_id || term.campus_id === activeProgram?.campus_id),
  );
  const [revisionId, setRevisionId] = useState(firstId(revisions));
  const [termId, setTermId] = useState(firstId(terms));
  const selectedRevision = revisions.find((revision) => revision.id === revisionId) ?? revisions[0];
  const selectedTerm = terms.find((term) => term.id === termId) ?? terms[0];
  const admissionDate = selectedTerm?.starts_at.slice(0, 10);
  const revisionApplies = Boolean(
    selectedRevision && admissionDate &&
    selectedRevision.effective_from <= admissionDate &&
    (!selectedRevision.effective_to || admissionDate < selectedRevision.effective_to),
  );
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

  function chooseInstitution(nextInstitutionId: string) {
    setInstitutionId(nextInstitutionId);
    const nextPrograms = catalog.programs.filter(
      (program) => program.institution_id === nextInstitutionId,
    );
    const nextProgram = nextPrograms[0];
    setProgramId(nextProgram?.id ?? "");
    const nextPlan = catalog.plans.find((plan) => plan.program_id === nextProgram?.id);
    setPlanId(nextPlan?.id ?? "");
    setRevisionId(catalog.revisions.find((revision) => revision.plan_id === nextPlan?.id)?.id ?? "");
    setTermId(catalog.terms.find((term) => term.institution_id === nextInstitutionId && (!term.campus_id || term.campus_id === nextProgram?.campus_id))?.id ?? "");
  }

  function chooseProgram(nextProgramId: string) {
    setProgramId(nextProgramId);
    const nextPlan = catalog.plans.find((plan) => plan.program_id === nextProgramId);
    const nextProgram = catalog.programs.find((program) => program.id === nextProgramId);
    setPlanId(nextPlan?.id ?? "");
    setRevisionId(catalog.revisions.find((revision) => revision.plan_id === nextPlan?.id)?.id ?? "");
    setTermId(catalog.terms.find((term) => term.institution_id === nextProgram?.institution_id && (!term.campus_id || term.campus_id === nextProgram?.campus_id))?.id ?? "");
  }

  function choosePlan(nextPlanId: string) {
    setPlanId(nextPlanId);
    setRevisionId(catalog.revisions.find((revision) => revision.plan_id === nextPlanId)?.id ?? "");
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const selectedPlan = plans.find((plan) => plan.id === planId) ?? plans[0];
    if (!institutionId || !activeProgram || !selectedPlan || !selectedRevision || !selectedTerm) {
      setError("Completa el programa, el plan, la revisión y el período de admisión.");
      return;
    }
    const payload: AdminEnrollmentCreatePayload = {
      email: String(form.get("email") ?? ""),
      temporary_password: String(form.get("temporary_password") ?? ""),
      display_name: String(form.get("display_name") ?? ""),
      student_number: String(form.get("student_number") ?? ""),
      cohort_code: String(form.get("cohort_code") ?? ""),
      institution_id: institutionId,
      program_id: activeProgram.id,
      plan_id: selectedPlan.id,
      revision_basis_id: selectedRevision.id,
      admission_term_id: selectedTerm.id,
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
      setMessage(`Cuenta y matrícula creadas para ${result.data.display_name}.`);
      formElement.reset();
    });
  }

  const revisionStatus = (status: string) => ({ PUBLISHED: "Publicada", SUPERSEDED: "Reemplazada", RETIRED: "Retirada" })[status] ?? "No disponible";
  const revisionValidity = (revision: typeof selectedRevision) => revision ? `${revision.effective_from} → ${revision.effective_to ?? "vigente"}` : "";
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
          {searching ? <p className="empty-copy" role="status">Buscando matrículas…</p> : enrollments.length ? <div className="student-admin-rows">{enrollments.map((enrollment) => <article key={enrollment.id}><div><strong>{enrollment.display_name || enrollment.email}</strong><span>{enrollment.student_number || "Sin número"} · {enrollment.email}</span></div><div><span>{enrollment.program_name}</span><small>Plan {enrollment.plan_code} · ingreso {enrollment.admission_term_code}</small></div><StatusBadge tone={enrollment.status === "ACTIVE" ? "eligible" : "unknown"} label={enrollmentStatus(enrollment.status)} /></article>)}</div> : <p className="empty-copy">No hay matrículas que coincidan con la búsqueda.</p>}
          <nav className="pagination-controls" aria-label="Páginas de matrículas"><button type="button" className="button button-secondary" disabled={searching || page.previous_offset === null} onClick={() => void loadEnrollments(page.previous_offset ?? 0)}>Anterior</button><span>Página {Math.floor(page.offset / page.limit) + 1} de {Math.max(1, Math.ceil(total / page.limit))}</span><button type="button" className="button button-secondary" disabled={searching || page.next_offset === null} onClick={() => void loadEnrollments(page.next_offset ?? 0)}>Siguiente</button></nav>
        </section>

        <section className="panel student-admin-create" aria-labelledby="create-student-title">
          <div className="section-heading"><div><p className="eyebrow">Alta completa</p><h2 id="create-student-title">Crear estudiante</h2></div></div>
          <form onSubmit={submit} className="student-admin-form">
            <fieldset><legend>Identidad y acceso</legend><label className="field-group"><span>Nombre completo</span><input name="display_name" required autoComplete="name" /></label><label className="field-group"><span>Correo de acceso</span><input name="email" type="email" required autoComplete="off" /></label><label className="field-group"><span>Número estudiantil</span><input name="student_number" required /></label><label className="field-group"><span>Contraseña temporal</span><input name="temporary_password" type="password" required minLength={12} autoComplete="new-password" /><small>Compártela por un canal seguro; nunca se guarda ni se vuelve a mostrar en texto claro.</small></label></fieldset>
            <fieldset><legend>Vinculación académica</legend><label className="field-group"><span>Institución</span><select value={institutionId} onChange={(event) => chooseInstitution(event.target.value)} required>{catalog.institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}</select></label><label className="field-group"><span>Programa y sede</span><select value={activeProgram?.id ?? ""} onChange={(event) => chooseProgram(event.target.value)} required>{programs.map((program) => <option key={program.id} value={program.id}>{program.name} · {program.campus_name}</option>)}</select></label><label className="field-group"><span>Plan</span><select value={activePlan?.id ?? ""} onChange={(event) => choosePlan(event.target.value)} required>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.code} · {plan.title}</option>)}</select></label><label className="field-group"><span>Revisión base</span><select value={revisionId} onChange={(event) => setRevisionId(event.target.value)} required>{revisions.map((revision) => <option key={revision.id} value={revision.id}>{revision.code} · {revisionStatus(revision.status)} · {revisionValidity(revision)}</option>)}</select></label><label className="field-group"><span>Período de ingreso</span><select required value={termId} onChange={(event) => setTermId(event.target.value)}>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · {termStatus(term.status)}</option>)}</select></label>{selectedRevision && selectedTerm && !revisionApplies ? <Alert tone="warning">La revisión elegida no cubre la fecha de ingreso. La matrícula se creará como «Requiere revisión» y no se asumirá una regla curricular.</Alert> : null}<label className="field-group"><span>Cohorte (opcional)</span><input name="cohort_code" /></label></fieldset>
            <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Creando…" : "Crear cuenta y matrícula"}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
