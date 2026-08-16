import Link from "next/link";

const navigation = [
  ["Resumen", "/"],
  ["Mi malla", "/curriculum"],
  ["Auditoría", "/audit"],
  ["Dependencias", "/graph"],
  ["Planificador", "/planner"],
  ["Oferta", "/offerings"],
  ["Historia", "/history"],
] as const;

export default function HomePage() {
  return (
    <main className="app-frame">
      <aside className="sidebar" aria-label="Navegación principal">
        <Link className="brand" href="/" aria-label="Curriculum Navigator, inicio">
          <span className="brand-mark" aria-hidden="true">CN</span>
          <span>
            <strong>Curriculum</strong>
            <span>Navigator</span>
          </span>
        </Link>
        <nav className="main-nav">
          {navigation.map(([label, href], index) => (
            <Link className={index === 0 ? "nav-link active" : "nav-link"} href={href} key={href}>
              <span className="nav-index" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="status-dot" aria-hidden="true" />
          <span>Datos normativos con procedencia visible</span>
        </div>
      </aside>

      <section className="content-area">
        <header className="topbar">
          <div>
            <p className="eyebrow">Espacio académico</p>
            <h1>Entiende tu siguiente movimiento</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" aria-label="Abrir centro de notificaciones">◌</button>
            <div className="profile-chip" aria-label="Perfil de estudiante">ER<span aria-hidden="true">⌄</span></div>
          </div>
        </header>

        <div className="content-grid">
          <section className="hero panel">
            <div>
              <p className="eyebrow accent">Estadística · Bogotá · Plan 2514</p>
              <h2>Tu mapa académico,<br /><em>sin adivinar las reglas.</em></h2>
              <p className="hero-copy">Consulta progreso, requisitos, bloqueos y rutas posibles con una explicación que siempre apunta a su evidencia.</p>
              <div className="hero-actions">
                <Link className="button button-primary" href="/audit">Abrir auditoría <span aria-hidden="true">→</span></Link>
                <Link className="text-link" href="/curriculum">Explorar la malla</Link>
              </div>
            </div>
            <div className="hero-orbit" aria-hidden="true">
              <div className="orbit orbit-one"><span>141</span></div>
              <div className="orbit orbit-two"><span>80%</span></div>
              <div className="orbit-core"><span>CN</span></div>
            </div>
          </section>

          <section className="metric-row" aria-label="Resumen de progreso">
            <article className="metric-card panel">
              <div className="metric-label">Créditos aprobados <span className="info-dot" title="Calculado desde intentos reconocibles">i</span></div>
              <div className="metric-value">0 <small>/ 141</small></div>
              <div className="progress-track"><span style={{ width: "0%" }} /></div>
              <p className="metric-footnote">Aún no has cargado historia</p>
            </article>
            <article className="metric-card panel metric-highlight">
              <div className="metric-label">Próximo desbloqueo</div>
              <div className="metric-value course-code">2016366</div>
              <p className="metric-footnote">Estadística descriptiva y exploratoria</p>
              <span className="tag tag-neutral">Revisa requisitos</span>
            </article>
            <article className="metric-card panel">
              <div className="metric-label">Revisión normativa</div>
              <div className="metric-value revision-value">2514<span> · AC496-2023</span></div>
              <p className="metric-footnote"><span className="status-dot" aria-hidden="true" /> Fuente archivada y trazable</p>
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
                <span><strong>Explora el plan</strong><small>Conoce los 141 créditos y sus agrupaciones</small></span>
                <span aria-hidden="true">↗</span>
              </Link>
              <Link className="start-card" href="/planner">
                <span className="start-number">03</span>
                <span><strong>Crea un escenario</strong><small>Planea sin alterar tu historia real</small></span>
                <span aria-hidden="true">↗</span>
              </Link>
            </div>
          </section>

          <footer className="content-footer">
            <span>Curriculum Navigator · versión del motor visible en cada auditoría</span>
            <Link href="/sources">Sobre la evidencia</Link>
          </footer>
        </div>
      </section>
    </main>
  );
}
