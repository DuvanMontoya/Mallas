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
  const raw = text(value);
  return ({ SATISFIED: "Cumplido", UNSATISFIED: "Pendiente", UNKNOWN: "Por verificar", INCOMPLETE: "Incompleto", READY: "Disponible", PASSED: "Aprobado", BLOCKED: "Bloqueado" } as Record<string, string>)[raw] ?? raw.replaceAll("_", " ").toLocaleLowerCase("es-CO");
}

function requirementLabel(value: unknown): string {
  const raw = text(value, "");
  if (raw.includes("ENROLLMENT_PREREQUISITE")) return "Prerrequisitos de matrícula pendientes";
  if (raw.includes("DEPENDENCY_TYPE_UNKNOWN")) return "Tipo de dependencia por verificar";
  if (raw.includes("CREDIT")) return "Créditos requeridos pendientes";
  if (raw.includes("COURSE")) return "Asignatura requerida pendiente";
  return "Requisito curricular pendiente";
}

function TraceCode({ value }: { value: string }) {
  return <details><summary>Ver trazabilidad técnica</summary><code>{value}</code></details>;
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

  if (analytics.data_state === "ENROLLMENT_NEEDS_REVIEW") {
    return (
      <div className="analytics-page">
        <header className="route-command">
          <div><p className="eyebrow">Analítica personal</p><h1>Primero confirma tu revisión curricular</h1></div>
          <Link className="button button-primary" href="/curriculum">Ver malla pública</Link>
        </header>
        <section className="analytics-warning panel" role="status">
          <p>Administración debe confirmar qué revisión del plan corresponde a tu período de ingreso. Hasta entonces no calculamos porcentajes ni recomendaciones que podrían ser incorrectos.</p>
          <small>{text(analytics.program_name)} · Plan {text(analytics.plan_code)}</small>
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
      <section className="analytics-decision-hero">
        <div>
          <p className="eyebrow">Analítica personal</p>
          <h1>Evolución académica</h1>
          <span>{progress}% completado · {number(credits.remaining)} créditos restantes</span>
          <div className="audit-hero-actions"><Link className="button button-primary" href="/curriculum">Volver a mi malla</Link><Link className="button button-secondary" href="/audit">Ver lo que me falta</Link></div>
        </div>
        <div className="analytics-privacy-card">
          <strong>{hasSnapshot ? "Datos verificados" : "Datos pendientes"}</strong>
          <span>{hasSnapshot ? `Actualizados el ${dateLabel(analytics.as_of)}` : "Todavía no existe una auditoría publicada para esta matrícula."}</span>
          <small>{text(analytics.program_name)} · Plan {text(analytics.plan_code)}</small>
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
              <MetricCard label="Requisitos pendientes" value={String(number(requirements.remaining_count))} detail={`${number(requirements.unknown_count)} por verificar`} />
            </div>
            <div className="analytics-progress-wrap">
              <div className="analytics-progress-label"><strong>{progress}%</strong><span>avance por créditos aplicados</span></div>
              <ProgressBar value={progress} />
              <p className="analytics-note">Este porcentaje describe créditos aplicados; los requisitos no crediticios y datos por verificar también deben cerrarse antes del grado.</p>
            </div>
          </section>

          <details className="analytics-disclosure panel"><summary><span><b>Ver evolución histórica</b><small>{trend.length} resultados de auditoría conservados</small></span></summary><section className="analytics-section" aria-labelledby="analytics-trend-title">
            <div className="analytics-section-heading"><div><p className="eyebrow">Evolución</p><h2 id="analytics-trend-title">Snapshots de avance</h2></div></div>
            {trend.length === 0 ? <EmptyState>No hay snapshots históricos disponibles.</EmptyState> : (
              <div className="analytics-table-wrap">
                <table className="analytics-table">
                  <caption>Cada fila es un resultado de auditoría persistido; no se interpolan datos faltantes.</caption>
                  <thead><tr><th scope="col">Corte</th><th scope="col">Aplicados</th><th scope="col">Avance</th><th scope="col">Estado</th><th scope="col">Por verificar</th></tr></thead>
                  <tbody>{trend.map((item) => <tr key={`${text(item.captured_at)}-${text(item.result_hash)}`}><th scope="row">{dateLabel(item.captured_at)}</th><td>{number(item.applied_credits)} / {number(item.required_credits)}</td><td>{number(item.progress_percent)}%</td><td><span className="analytics-status">{statusLabel(item.status)}</span></td><td>{number(item.unknown_count)}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </section></details>

          <section className="analytics-two-column">
            <div className="analytics-section" aria-labelledby="analytics-bottlenecks-title">
              <div className="analytics-section-heading"><div><p className="eyebrow">Bloqueos</p><h2 id="analytics-bottlenecks-title">Cursos críticos</h2></div></div>
              {criticalCourses.length === 0 ? <EmptyState>La auditoría no reporta cursos con requisitos bloqueados o ambiguos.</EmptyState> : (
                <>
                  <ul className="analytics-list">{criticalCourses.slice(0, 6).map((item) => { const codes = values(item.requirement_codes); return <li key={text(item.course_code)}><div><strong>{text(item.course_code)}</strong><span>{requirementLabel(codes[0])}</span>{codes.length ? <TraceCode value={codes.join(", ")} /> : null}</div><span className={`analytics-status analytics-status-${text(item.state, "unknown").toLowerCase()}`}>{statusLabel(item.state)}</span></li>; })}</ul>
                  {criticalCourses.length > 6 ? <details className="analytics-disclosure"><summary>Ver los {criticalCourses.length - 6} cursos restantes</summary><ul className="analytics-list">{criticalCourses.slice(6).map((item) => { const codes = values(item.requirement_codes); return <li key={text(item.course_code)}><div><strong>{text(item.course_code)}</strong><span>{requirementLabel(codes[0])}</span>{codes.length ? <TraceCode value={codes.join(", ")} /> : null}</div><span className={`analytics-status analytics-status-${text(item.state, "unknown").toLowerCase()}`}>{statusLabel(item.state)}</span></li>; })}</ul></details> : null}
                </>
              )}
            </div>
            <div className="analytics-section" aria-labelledby="analytics-requirements-title">
              <div className="analytics-section-heading"><div><p className="eyebrow">Trazabilidad</p><h2 id="analytics-requirements-title">Requisitos que faltan</h2></div></div>
              {rows(requirements.remaining).length === 0 ? <EmptyState>No hay requisitos pendientes en este snapshot.</EmptyState> : (
                <ul className="analytics-list">{rows(requirements.remaining).slice(0, 12).map((item) => { const code = text(item.code); const owner = text(item.owner_course_code, ""); return <li key={code}><div><strong>{requirementLabel(code)}</strong><span>{owner ? `Asignatura ${owner}` : "Regla del plan"}</span><TraceCode value={code} /></div><span className="analytics-status">{statusLabel(item.status)}</span></li>; })}</ul>
              )}
            </div>
          </section>

          <section className="analytics-section" aria-labelledby="analytics-scenarios-title">
            <div className="analytics-section-heading"><div><p className="eyebrow">Planificación</p><h2 id="analytics-scenarios-title">Comparación de escenarios</h2></div><Link className="small-link" href="/planner">Abrir planificador →</Link></div>
            {scenarios.length === 0 ? <EmptyState>Aún no hay proyecciones de escenarios persistidas.</EmptyState> : (
              <div className="analytics-table-wrap"><table className="analytics-table"><caption>Las proyecciones son privadas y no alteran la historia académica oficial.</caption><thead><tr><th scope="col">Escenario</th><th scope="col">Cursos planeados</th><th scope="col">Avance proyectado</th><th scope="col">Por verificar</th><th scope="col">Corte</th></tr></thead><tbody>{scenarios.map((item) => <tr key={`${text(item.name)}-${text(item.generated_at)}`}><th scope="row">{text(item.name)}</th><td>{number(item.planned_course_count)}</td><td>{number(item.progress_percent)}%</td><td>{number(item.unknown_count)}</td><td>{dateLabel(item.generated_at)}</td></tr>)}</tbody></table></div>
            )}
          </section>
        </>
      ) : null}

      <details className="analytics-disclosure panel"><summary><span><b>Cómo se calculan estas métricas</b><small>Fuentes, privacidad y nivel de evidencia</small></span></summary><section className="analytics-section" aria-labelledby="analytics-definitions-title">
        <div className="analytics-section-heading"><div><p className="eyebrow">Metodología visible</p><h2 id="analytics-definitions-title">Qué significa cada métrica</h2></div></div>
        <div className="analytics-definition-grid">{definitions.map((definition) => <article key={definition.key}><h3>{definition.label}</h3><p>{definition.description}</p><details><summary>Detalle técnico</summary><code>{definition.source}</code><span>{statusLabel(definition.epistemic_status)} · información privada</span></details></article>)}</div>
      </section></details>
    </div>
  );
}
