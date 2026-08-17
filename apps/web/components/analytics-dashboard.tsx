import Link from "next/link";

import type { ApiFailure, StudentAnalytics } from "@/lib/api";

type JsonRecord = Record<string, unknown>;

function record(value: unknown): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as JsonRecord) : {};
}

function rows(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.map(record) : [];
}

function values(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function text(value: unknown, fallback = "—"): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function number(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function dateLabel(value: unknown): string {
  if (typeof value !== "string") return "sin fecha";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("es-CO", { dateStyle: "medium" }).format(date);
}

function statusLabel(value: unknown): string {
  return text(value).replaceAll("_", " ");
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="analytics-metric panel">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ProgressBar({ value }: { value: number }) {
  const bounded = Math.min(100, Math.max(0, value));
  return (
    <div className="analytics-progress" role="progressbar" aria-label="Avance crediticio" aria-valuemin={0} aria-valuemax={100} aria-valuenow={bounded}>
      <span style={{ width: `${bounded}%` }} />
    </div>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="analytics-empty">{children}</p>;
}

export function AnalyticsDashboard({ analytics, failure }: { analytics: StudentAnalytics | null; failure: ApiFailure | null }) {
  if (failure || !analytics) {
    return (
      <div className="analytics-page">
        <section className="analytics-hero panel">
          <div>
            <p className="eyebrow">Analítica explicable</p>
            <h1>Entiende tu avance con datos auditados.</h1>
            <p>Esta vista sólo muestra métricas derivadas de auditorías persistidas y reglas curriculares publicadas.</p>
          </div>
          <div className="analytics-privacy-card">
            <strong>Sesión requerida</strong>
            <span>{failure?.problem?.detail ?? "Inicia sesión para consultar tus métricas privadas."}</span>
            <Link className="button button-primary" href="/login">Iniciar sesión</Link>
          </div>
        </section>
      </div>
    );
  }

  const metrics = record(analytics.metrics);
  const credits = record(metrics.credits);
  const requirements = record(metrics.requirements);
  const trend = rows(metrics.trend);
  const criticalCourses = rows(metrics.critical_courses);
  const scenarios = rows(metrics.scenarios);
  const definitions = analytics.definitions;
  const progress = number(credits.progress_percent);
  const hasSnapshot = analytics.data_state === "PERSISTED_PUBLISHED_AUDIT";

  return (
    <div className="analytics-page">
      <section className="analytics-hero panel">
        <div>
          <p className="eyebrow">Analítica estudiantil · {text(analytics.program_code)}</p>
          <h1>Tu avance, explicado sin cajas negras.</h1>
          <p>
            {text(analytics.program_name)} · plan {text(analytics.plan_code)} · revisión {text(analytics.revision_code)}.
            Las cifras se leen del último resultado de auditoría publicado y conservan su fecha de corte.
          </p>
        </div>
        <div className="analytics-privacy-card">
          <strong>{hasSnapshot ? "Snapshot verificable" : "Sin snapshot publicado"}</strong>
          <span>{hasSnapshot ? `Corte: ${dateLabel(analytics.as_of)}` : "Todavía no existe una auditoría persistida sobre una revisión publicada."}</span>
          <span className="analytics-state-code">{text(analytics.data_state)}</span>
        </div>
      </section>

      {analytics.warnings.length > 0 ? (
        <section className="analytics-warning panel" role="status">
          {analytics.warnings.map((warning) => <p key={warning}>{warning}</p>)}
        </section>
      ) : null}

      {hasSnapshot ? (
        <>
          <section className="analytics-section" aria-labelledby="analytics-progress-title">
            <div className="analytics-section-heading">
              <div><p className="eyebrow">Resultado de auditoría</p><h2 id="analytics-progress-title">Progreso crediticio</h2></div>
              <span className="analytics-as-of">{dateLabel(analytics.as_of)}</span>
            </div>
            <div className="analytics-metric-grid">
              <MetricCard label="Créditos aplicados" value={`${number(credits.applied)} / ${number(credits.required)}`} detail="Asignados a requisitos" />
              <MetricCard label="Créditos restantes" value={String(number(credits.remaining))} detail="Según la revisión publicada" />
              <MetricCard label="Requisitos pendientes" value={String(number(requirements.remaining_count))} detail={`${number(requirements.unknown_count)} en UNKNOWN`} />
              <MetricCard label="Estado del motor" value={statusLabel(record(analytics.snapshot).status)} detail={`Motor ${text(record(analytics.snapshot).engine_version)}`} />
            </div>
            <div className="analytics-progress-wrap">
              <div className="analytics-progress-label"><strong>{progress}%</strong><span>avance por créditos aplicados</span></div>
              <ProgressBar value={progress} />
              <p className="analytics-note">Este porcentaje no certifica por sí solo el grado: los requisitos no crediticios y estados UNKNOWN siguen siendo vinculantes.</p>
            </div>
          </section>

          <section className="analytics-section" aria-labelledby="analytics-trend-title">
            <div className="analytics-section-heading"><div><p className="eyebrow">Evolución</p><h2 id="analytics-trend-title">Snapshots de avance</h2></div></div>
            {trend.length === 0 ? <EmptyState>No hay snapshots históricos disponibles.</EmptyState> : (
              <div className="analytics-table-wrap">
                <table className="analytics-table">
                  <caption>Cada fila es un resultado de auditoría persistido; no se interpolan datos faltantes.</caption>
                  <thead><tr><th scope="col">Corte</th><th scope="col">Aplicados</th><th scope="col">Avance</th><th scope="col">Estado</th><th scope="col">UNKNOWN</th></tr></thead>
                  <tbody>{trend.map((item) => <tr key={`${text(item.captured_at)}-${text(item.result_hash)}`}><th scope="row">{dateLabel(item.captured_at)}</th><td>{number(item.applied_credits)} / {number(item.required_credits)}</td><td>{number(item.progress_percent)}%</td><td><span className="analytics-status">{statusLabel(item.status)}</span></td><td>{number(item.unknown_count)}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </section>

          <section className="analytics-two-column">
            <div className="analytics-section" aria-labelledby="analytics-bottlenecks-title">
              <div className="analytics-section-heading"><div><p className="eyebrow">Bloqueos</p><h2 id="analytics-bottlenecks-title">Cursos críticos</h2></div></div>
              {criticalCourses.length === 0 ? <EmptyState>La auditoría no reporta cursos con requisitos bloqueados o ambiguos.</EmptyState> : (
                <ul className="analytics-list">{criticalCourses.map((item) => <li key={text(item.course_code)}><div><strong>{text(item.course_code)}</strong><span>{values(item.requirement_codes).join(", ") || "Requisito pendiente"}</span></div><span className={`analytics-status analytics-status-${text(item.state, "unknown").toLowerCase()}`}>{statusLabel(item.state)}</span></li>)}</ul>
              )}
            </div>
            <div className="analytics-section" aria-labelledby="analytics-requirements-title">
              <div className="analytics-section-heading"><div><p className="eyebrow">Trazabilidad</p><h2 id="analytics-requirements-title">Requisitos que faltan</h2></div></div>
              {rows(requirements.remaining).length === 0 ? <EmptyState>No hay requisitos pendientes en este snapshot.</EmptyState> : (
                <ul className="analytics-list">{rows(requirements.remaining).slice(0, 12).map((item) => <li key={text(item.code)}><div><strong>{text(item.code)}</strong><span>{text(item.owner_course_code, text(item.purpose))}</span></div><span className="analytics-status">{statusLabel(item.status)}</span></li>)}</ul>
              )}
            </div>
          </section>

          <section className="analytics-section" aria-labelledby="analytics-scenarios-title">
            <div className="analytics-section-heading"><div><p className="eyebrow">Planificación</p><h2 id="analytics-scenarios-title">Comparación de escenarios</h2></div><Link className="small-link" href="/planner">Abrir planificador →</Link></div>
            {scenarios.length === 0 ? <EmptyState>Aún no hay proyecciones de escenarios persistidas.</EmptyState> : (
              <div className="analytics-table-wrap"><table className="analytics-table"><caption>Las proyecciones son privadas y no alteran la historia académica oficial.</caption><thead><tr><th scope="col">Escenario</th><th scope="col">Cursos planeados</th><th scope="col">Avance proyectado</th><th scope="col">UNKNOWN</th><th scope="col">Corte</th></tr></thead><tbody>{scenarios.map((item) => <tr key={`${text(item.name)}-${text(item.generated_at)}`}><th scope="row">{text(item.name)}</th><td>{number(item.planned_course_count)}</td><td>{number(item.progress_percent)}%</td><td>{number(item.unknown_count)}</td><td>{dateLabel(item.generated_at)}</td></tr>)}</tbody></table></div>
            )}
          </section>
        </>
      ) : null}

      <section className="analytics-section" aria-labelledby="analytics-definitions-title">
        <div className="analytics-section-heading"><div><p className="eyebrow">Metodología visible</p><h2 id="analytics-definitions-title">Qué significa cada métrica</h2></div></div>
        <div className="analytics-definition-grid">{definitions.map((definition) => <article key={definition.key}><h3>{definition.label}</h3><p>{definition.description}</p><code>{definition.source}</code><span>{definition.epistemic_status} · {definition.privacy}</span></article>)}</div>
      </section>
    </div>
  );
}
