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
    <div className="content-grid">
      <section className="hero panel">
        <div>
          <p className="eyebrow accent">Gobernanza curricular · plan 2514</p>
          <h1>La malla publicada,<br /><em>antes que el backoffice.</em></h1>
          <p className="hero-copy">Inspecciona primero el producto que reciben los estudiantes y entra a fuentes sólo cuando necesites revisar evidencia o una nueva revisión.</p>
          <div className="hero-actions"><Link className="button button-primary" href="/curriculum">Abrir la malla <span aria-hidden="true">→</span></Link><Link className="text-link" href="/sources">Gobernar fuentes</Link></div>
        </div>
      </section>
      <section className="panel empty-state-panel" aria-labelledby="editorial-start-title"><div className="section-heading"><div><p className="eyebrow">Flujo editorial</p><h2 id="editorial-start-title">Publica sin perder procedencia</h2></div><span className="tag tag-outline">Separación de funciones</span></div><div className="start-grid"><Link className="start-card" href="/curriculum"><span className="start-number">01</span><span><strong>Verifica la experiencia</strong><small>Malla, reglas visibles y estados no normativos</small></span><span aria-hidden="true">↗</span></Link><Link className="start-card" href="/sources"><span className="start-number">02</span><span><strong>Revisa evidencia</strong><small>Snapshots, propuestas y recibos inmutables</small></span><span aria-hidden="true">↗</span></Link><Link className="start-card" href="/graph"><span className="start-number">03</span><span><strong>Inspecciona dependencias</strong><small>Relaciones completas y alternativa textual</small></span><span aria-hidden="true">↗</span></Link></div></section>
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
          <h1 id="student-command-title">¿Qué sigue en tu carrera?</h1>
          <p>Empieza por tu malla: allí ves lo aprobado, lo que cursas, lo que puedes matricular y por qué lo demás sigue bloqueado.</p>
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
