import { cookies } from "next/headers";
import Link from "next/link";

import { AcademicDashboard } from "@/components/academic-dashboard";
import { getAcademicOverview, getSessionSnapshot } from "@/lib/api";

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

export default async function HomePage() {
  const headers = await requestHeaders();
  const session = await getSessionSnapshot(headers);
  const editorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (editorialOnly) return <EditorialHome />;
  const overview = await getAcademicOverview({ headers });

  return (
    <div className="content-grid">
      <section className="hero panel">
        <div>
          <p className="eyebrow accent">Universidad Nacional · Estadística</p>
          <h1>Tu mapa académico,<br /><em>con reglas visibles.</em></h1>
          <p className="hero-copy">Consulta progreso, requisitos, bloqueos y rutas posibles con una explicación que siempre apunta a su evidencia.</p>
          <div className="hero-actions">
            <Link className="button button-primary" href="/curriculum">Explorar la malla <span aria-hidden="true">→</span></Link>
            <Link className="text-link" href="/audit">Abrir auditoría</Link>
          </div>
        </div>
      </section>

      {overview.data ? <AcademicDashboard overview={overview.data} failure={overview.failure} /> : <EmptyDashboardHome />}
    </div>
  );
}
