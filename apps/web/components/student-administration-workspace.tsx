"use client";

import { useMemo, useState, useTransition } from "react";

import {
  createAdminEnrollment,
  type AdminEnrollment,
  type AdminEnrollmentCreatePayload,
  type StudentAdminCatalog,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

function firstId<T extends { id: string }>(items: T[]) {
  return items[0]?.id ?? "";
}

export function StudentAdministrationWorkspace({
  catalog,
  initialEnrollments,
}: {
  catalog: StudentAdminCatalog;
  initialEnrollments: AdminEnrollment[];
}) {
  const [enrollments, setEnrollments] = useState(initialEnrollments);
  const [search, setSearch] = useState("");
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
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

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
    const selectedRevision = revisions.find((revision) => revision.id === revisionId) ?? revisions[0];
    const selectedTerm = terms.find((term) => term.id === termId);
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
      setEnrollments((current) => [result.data as AdminEnrollment, ...current]);
      setMessage(`Cuenta y matrícula creadas para ${result.data.display_name}.`);
      formElement.reset();
    });
  }

  const normalizedSearch = search.trim().toLocaleLowerCase("es-CO");
  const visibleEnrollments = enrollments.filter((enrollment) =>
    [enrollment.display_name, enrollment.email, enrollment.student_number, enrollment.plan_code]
      .join(" ")
      .toLocaleLowerCase("es-CO")
      .includes(normalizedSearch),
  );

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
          <div className="section-heading"><div><p className="eyebrow">Matrículas activas y registradas</p><h2 id="managed-students-title">{visibleEnrollments.length} estudiantes</h2></div></div>
          {visibleEnrollments.length ? <div className="student-admin-rows">{visibleEnrollments.map((enrollment) => <article key={enrollment.id}><div><strong>{enrollment.display_name || enrollment.email}</strong><span>{enrollment.student_number || "Sin número"} · {enrollment.email}</span></div><div><span>{enrollment.program_name}</span><small>Plan {enrollment.plan_code} · ingreso {enrollment.admission_term_code}</small></div><StatusBadge tone={enrollment.status === "ACTIVE" ? "eligible" : "unknown"} label={enrollment.status === "ACTIVE" ? "Activa" : enrollment.status} /></article>)}</div> : <p className="empty-copy">No hay matrículas que coincidan con la búsqueda.</p>}
        </section>

        <section className="panel student-admin-create" aria-labelledby="create-student-title">
          <div className="section-heading"><div><p className="eyebrow">Alta completa</p><h2 id="create-student-title">Crear estudiante</h2></div></div>
          <form onSubmit={submit} className="student-admin-form">
            <fieldset><legend>Identidad y acceso</legend><label className="field-group"><span>Nombre completo</span><input name="display_name" required autoComplete="name" /></label><label className="field-group"><span>Correo de acceso</span><input name="email" type="email" required autoComplete="off" /></label><label className="field-group"><span>Número estudiantil</span><input name="student_number" required /></label><label className="field-group"><span>Contraseña temporal</span><input name="temporary_password" type="password" required minLength={12} autoComplete="new-password" /><small>Compártela por un canal seguro; nunca se guarda ni se vuelve a mostrar en texto claro.</small></label></fieldset>
            <fieldset><legend>Vinculación académica</legend><label className="field-group"><span>Institución</span><select value={institutionId} onChange={(event) => chooseInstitution(event.target.value)} required>{catalog.institutions.map((institution) => <option key={institution.id} value={institution.id}>{institution.name}</option>)}</select></label><label className="field-group"><span>Programa y sede</span><select value={activeProgram?.id ?? ""} onChange={(event) => chooseProgram(event.target.value)} required>{programs.map((program) => <option key={program.id} value={program.id}>{program.name} · {program.campus_name}</option>)}</select></label><label className="field-group"><span>Plan</span><select value={activePlan?.id ?? ""} onChange={(event) => choosePlan(event.target.value)} required>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.code} · {plan.title}</option>)}</select></label><label className="field-group"><span>Revisión base</span><select value={revisionId} onChange={(event) => setRevisionId(event.target.value)} required>{revisions.map((revision) => <option key={revision.id} value={revision.id}>{revision.code} · {revision.status}</option>)}</select></label><label className="field-group"><span>Período de ingreso</span><select required value={termId} onChange={(event) => setTermId(event.target.value)}>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · {term.status}</option>)}</select></label><label className="field-group"><span>Cohorte (opcional)</span><input name="cohort_code" /></label></fieldset>
            <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Creando…" : "Crear cuenta y matrícula"}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
