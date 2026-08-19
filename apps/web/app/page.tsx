import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getAcademicOverview, getSessionSnapshot, type AcademicOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

async function requestHeaders() {
  try {
    const cookieHeader = (await cookies()).toString();
    return cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    // Vitest renders the Server Component outside a request context. The API
    // boundary will then return the honest unavailable state.
    return undefined;
  }
}

type EntryState = "anonymous" | "unavailable" | "enrollment-missing" | "enrollment-review";

function EmptyDashboardHome({ state }: { state: EntryState }) {
  const unavailable = state === "unavailable";
  const enrollmentMissing = state === "enrollment-missing";
  const enrollmentReview = state === "enrollment-review";
  return (
    <section className="panel compact-entry" aria-labelledby="start-title"><div><p className="eyebrow">{unavailable ? "Servicio temporalmente no disponible" : enrollmentReview ? "Vinculación curricular en revisión" : enrollmentMissing ? "Acceso académico pendiente" : "Plan 2514 · Estadística"}</p><h1 id="start-title">{unavailable ? "No pudimos cargar tu estado académico" : enrollmentReview ? "Aún no podemos determinar tu avance" : enrollmentMissing ? "Tu cuenta aún no tiene una matrícula vinculada" : "Explora la malla curricular"}</h1><p>{unavailable ? "Tus datos no se modificaron. Puedes reintentar o consultar la malla pública." : enrollmentReview ? "La administración debe confirmar qué revisión corresponde a tu ingreso. Puedes consultar la malla pública, pero no mostraremos elegibilidad ni faltantes como definitivos." : enrollmentMissing ? "La vinculación debe resolverla la administración académica; importar un archivo todavía no está habilitado para esta cuenta." : "Consulta obligatorias, opciones y prerrequisitos sin iniciar sesión."}</p></div><div className="compact-entry-actions"><Link className="button button-primary" href={unavailable ? "/" : "/curriculum"}>{unavailable ? "Reintentar" : "Abrir malla"}</Link>{state === "anonymous" ? <Link className="button button-secondary" href="/login">Iniciar sesión</Link> : unavailable ? <Link className="button button-secondary" href="/curriculum">Ver malla pública</Link> : null}</div></section>
  );
}

function EditorialHome() {
  return (
    <div className="editorial-home">
      <section className="editorial-command">
        <div>
          <p className="eyebrow accent">Administración curricular · Plan 2514</p>
          <h1>Administración curricular</h1>
        </div>
        <aside><span>Principio de trabajo</span><strong>Publicar sólo cuando reglas, impacto y evidencia sean comprensibles.</strong><small>Cada revisión publicada es inmutable y conserva su procedencia.</small></aside>
      </section>
      <section className="editorial-flow" aria-labelledby="editorial-start-title"><div className="section-heading"><div><p className="eyebrow">Una tarea a la vez</p><h2 id="editorial-start-title">¿Qué necesitas hacer?</h2></div></div><div className="editorial-flow-grid"><Link href="/curriculum"><span>01</span><div><strong>Validar la experiencia publicada</strong><small>Comprueba obligatorias, elecciones y explicación de bloqueos como las verá una persona.</small></div><b>Empezar →</b></Link><Link href="/sources"><span>02</span><div><strong>Revisar o publicar un cambio</strong><small>Trabaja con evidencia, diff semántico, impacto y separación de funciones.</small></div><b>Abrir →</b></Link><Link href="/graph"><span>03</span><div><strong>Investigar una dependencia</strong><small>Sigue prerrequisitos y desbloqueos sin alterar reglas desde la visualización.</small></div><b>Explorar →</b></Link><Link href="/admin/students"><span>04</span><div><strong>Gestionar estudiantes y matrículas</strong><small>Crea la cuenta, el perfil y la vinculación académica en un solo flujo auditado.</small></div><b>Abrir administración →</b></Link></div></section>
    </div>
  );
}

function StudentDecisionHome({ overview }: { overview: AcademicOverview }) {
  const overall = overview.audit.overall;
  const eligible = overview.eligible_courses;
  const next = eligible.length ? eligible : overview.next_unlocks;
  return (
    <div className="student-home">
      <section className="student-command" aria-labelledby="student-command-title">
        <div className="student-command-copy">
          <p className="eyebrow accent">Estadística · Plan {overview.enrollment.plan_code}</p>
          <h1 id="student-command-title">Mi carrera</h1>
          <div className="student-command-actions"><Link className="button button-primary" href="/curriculum">Ver mi malla <span aria-hidden="true">→</span></Link><Link className="text-link" href="/planner">Planear el próximo período</Link></div>
        </div>
        <div className="student-progress-summary">
          <span>Créditos aplicados</span>
          <strong>{overall.applied_credits}<small> / {overall.required_credits}</small></strong>
          <div className="student-progress-track" role="progressbar" aria-label="Créditos aplicados" aria-valuemin={0} aria-valuemax={overall.required_credits} aria-valuenow={overall.applied_credits}><span style={{ width: `${overall.credit_progress_percent}%` }} /></div>
          <small>{overall.credit_progress_percent}% del requisito de créditos. El grado también depende de obligatorias y requisitos externos.</small>
        </div>
      </section>

      <section className="student-next panel" aria-labelledby="student-next-title">
        <div className="student-next-intro">
          <p className="eyebrow">Decisión inmediata</p>
          <h2 id="student-next-title">{eligible.length ? "Puedes considerar estas asignaturas" : "Antes de recomendar una matrícula"}</h2>
          <p>{eligible.length ? `Hay ${eligible.length} opciones con elegibilidad verificada. Abre la malla para compararlas dentro de tu ruta.` : `${overview.unknowns.length} reglas o datos necesitan revisión. No vamos a inventar una recomendación hasta resolverlos.`}</p>
          <Link className="small-link" href={eligible.length ? "/curriculum?status=ELIGIBLE" : "/curriculum?status=UNKNOWN"}>{eligible.length ? "Ver todas las matriculables →" : "Ver qué falta verificar →"}</Link>
        </div>
        <div className="student-next-list">
          {next.slice(0, 4).map((course) => <Link key={course.code} href={course.href}><span>{course.code}</span><strong>{course.name}</strong><small>{"credits" in course && course.credits !== null ? `${course.credits} créditos` : "Ver requisitos"}</small></Link>)}
          {!next.length ? <div className="student-next-empty"><strong>No hay una siguiente asignatura confirmada.</strong><span>Revisa tu historia y los datos pendientes para habilitar una recomendación responsable.</span></div> : null}
        </div>
      </section>

      <section className="student-home-facts" aria-label="Estado académico resumido">
        <Link href="/history"><span>Tu historia</span><strong>{overview.history.passed_count} aprobadas · {overview.history.in_progress_count} en curso</strong><small>{overview.history.attempt_count} intentos registrados</small></Link>
        <Link href="/curriculum?status=BLOCKED"><span>Obligatorias pendientes</span><strong>{overview.mandatory_missing.length}</strong><small>Ábrelas en contexto dentro de la malla</small></Link>
        <Link href="/audit"><span>Datos por verificar</span><strong>{overview.unknowns.length}</strong><small>Revisa reglas y evidencia sin ruido en el inicio</small></Link>
      </section>
    </div>
  );
}

export default async function HomePage() {
  const headers = await requestHeaders();
  const session = await getSessionSnapshot(headers);
  if (session.user?.onboarding_required && !session.user.must_change_password) redirect("/onboarding");
  const editorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (editorialOnly) return <EditorialHome />;
  const overview = await getAcademicOverview({ headers });

  if (overview.data) return <StudentDecisionHome overview={overview.data} />;
  const enrollmentMissing = session.state === "authenticated" && overview.failure?.problem?.code?.toLocaleLowerCase("es-CO") === "enrollment_not_found";
  const enrollmentReview = session.state === "authenticated" && overview.failure?.problem?.code?.toLocaleLowerCase("es-CO") === "enrollment_needs_review";
  const entryState: EntryState = enrollmentReview
    ? "enrollment-review"
    : overview.failure?.unavailable || session.state === "unavailable" || (session.state === "authenticated" && !enrollmentMissing)
    ? "unavailable"
    : enrollmentMissing
      ? "enrollment-missing"
      : "anonymous";
  return <div className="content-grid"><EmptyDashboardHome state={entryState} /></div>;
}
