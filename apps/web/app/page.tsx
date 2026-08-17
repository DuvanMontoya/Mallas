import { cookies } from "next/headers";
import Link from "next/link";

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

function EmptyDashboardHome() {
  return (
    <>
      <section className="metric-row" aria-label="Resumen académico">
        <article className="metric-card panel">
          <div className="metric-label">Estado de tu historia</div>
          <div className="metric-value metric-value-neutral">—</div>
          <p className="metric-footnote">La auditoría se activa con hechos verificables.</p>
        </article>
        <article className="metric-card panel metric-highlight">
          <div className="metric-label">Próxima decisión</div>
          <div className="metric-value metric-value-neutral">Ver</div>
          <p className="metric-footnote">Explora requisitos y bloqueos explicables.</p>
          <span className="tag tag-neutral">Sin inferencias</span>
        </article>
        <article className="metric-card panel">
          <div className="metric-label">Procedencia</div>
          <div className="metric-value metric-value-neutral">Visible</div>
          <p className="metric-footnote"><span className="status-dot" aria-hidden="true" /> Cada regla apunta a su evidencia.</p>
          <Link className="small-link" href="/sources">Ver evidencia</Link>
        </article>
      </section>

      <section className="panel empty-state-panel" aria-labelledby="start-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Primer paso</p>
            <h2 id="start-title">Construye tu punto de partida</h2>
          </div>
          <span className="tag tag-outline">Sin historia todavía</span>
        </div>
        <div className="start-grid">
          <Link className="start-card" href="/curriculum">
            <span className="start-number">01</span>
            <span><strong>Explora la malla</strong><small>Conoce la revisión curricular y sus agrupaciones</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
          <Link className="start-card" href="/history/import">
            <span className="start-number">02</span>
            <span><strong>Carga tu historia</strong><small>CSV/JSON o registro guiado con vista previa</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
          <Link className="start-card" href="/planner">
            <span className="start-number">03</span>
            <span><strong>Crea un escenario</strong><small>Planea sin alterar tu historia real</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>
    </>
  );
}

function EditorialHome() {
  return (
    <div className="editorial-home">
      <section className="editorial-command">
        <div>
          <p className="eyebrow accent">Administración curricular · Plan 2514</p>
          <h1>Administración curricular</h1>
          <div className="hero-actions"><Link className="button button-primary" href="/curriculum">Revisar la malla publicada <span aria-hidden="true">→</span></Link><Link className="button button-secondary" href="/sources">Abrir bandeja editorial</Link></div>
        </div>
        <aside><span>Principio de trabajo</span><strong>Publicar sólo cuando reglas, impacto y evidencia sean comprensibles.</strong><small>Cada revisión publicada es inmutable y conserva su procedencia.</small></aside>
      </section>
      <section className="editorial-flow" aria-labelledby="editorial-start-title"><div className="section-heading"><div><p className="eyebrow">Una tarea a la vez</p><h2 id="editorial-start-title">¿Qué necesitas hacer?</h2></div></div><div className="editorial-flow-grid"><Link href="/curriculum"><span>01</span><div><strong>Validar la experiencia publicada</strong><small>Comprueba obligatorias, elecciones y explicación de bloqueos como las verá una persona.</small></div><b>Empezar →</b></Link><Link href="/sources"><span>02</span><div><strong>Revisar o publicar un cambio</strong><small>Trabaja con evidencia, diff semántico, impacto y separación de funciones.</small></div><b>Abrir →</b></Link><Link href="/graph"><span>03</span><div><strong>Investigar una dependencia</strong><small>Sigue prerrequisitos y desbloqueos sin alterar reglas desde la visualización.</small></div><b>Explorar →</b></Link></div></section>
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
  const editorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (editorialOnly) return <EditorialHome />;
  const overview = await getAcademicOverview({ headers });

  return overview.data ? <StudentDecisionHome overview={overview.data} /> : <div className="content-grid"><EmptyDashboardHome /></div>;
}
