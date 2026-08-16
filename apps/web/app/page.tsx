import Link from "next/link";

export default function HomePage() {
  return (
    <div className="content-grid">
      <section className="hero panel">
        <div>
          <p className="eyebrow accent">Universidad Nacional · Estadística</p>
          <h1>Tu mapa académico,<br /><em>con reglas visibles.</em></h1>
          <p className="hero-copy">Consulta progreso, requisitos, bloqueos y rutas posibles con una explicación que siempre apunta a su evidencia.</p>
          <div className="hero-actions">
            <Link className="button button-primary" href="/audit">Abrir auditoría <span aria-hidden="true">→</span></Link>
            <Link className="text-link" href="/curriculum">Explorar la malla</Link>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit orbit-one"><span>AST</span></div>
          <div className="orbit orbit-two"><span>DATA</span></div>
          <div className="orbit-core"><span>CN</span></div>
        </div>
      </section>

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
          <Link className="start-card" href="/history/import">
            <span className="start-number">01</span>
            <span><strong>Carga tu historia</strong><small>CSV/JSON o registro guiado con vista previa</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
          <Link className="start-card" href="/curriculum">
            <span className="start-number">02</span>
            <span><strong>Explora el plan</strong><small>Conoce la revisión curricular y sus agrupaciones</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
          <Link className="start-card" href="/planner">
            <span className="start-number">03</span>
            <span><strong>Crea un escenario</strong><small>Planea sin alterar tu historia real</small></span>
            <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>
    </div>
  );
}
