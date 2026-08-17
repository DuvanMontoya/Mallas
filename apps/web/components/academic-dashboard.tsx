import Link from "next/link";
import type { ReactNode } from "react";

import type { AcademicOverview, ApiComponents, ApiFailure } from "@/lib/api";

import {
  AuditWarning,
  ComponentProgressCard,
  CourseCard,
  CreditLedger,
  EmptyState,
  GroupProgressTable,
  RequirementExplanation,
  StatusBadge,
  UnknownState,
  type GroupProgressRow,
} from "./ui";
import type { StatusTone } from "./ui/status-badge";

type CourseOption = ApiComponents["schemas"]["CourseOptionView"];
type Requirement = ApiComponents["schemas"]["RequirementView"];
type RequirementReason = ApiComponents["schemas"]["RequirementReasonView"];

const statusLabels: Record<string, string> = {
  SATISFIED: "Cumplido",
  PASSED: "Aprobado",
  IN_PROGRESS: "En curso",
  ELIGIBLE: "Puedes cursarlo",
  UNSATISFIED: "Pendiente",
  BLOCKED: "Bloqueado",
  UNKNOWN: "Por verificar",
  NO_HISTORY: "Sin historia",
  INCOMPLETE: "Auditoría incompleta",
  READY: "Auditoría disponible",
  NOT_APPLICABLE: "No aplica",
};

function toneFor(status: string): StatusTone {
  if (["SATISFIED", "PASSED"].includes(status)) return "passed";
  if (["IN_PROGRESS"].includes(status)) return "in-progress";
  if (["ELIGIBLE"].includes(status)) return "eligible";
  if (["UNSATISFIED", "BLOCKED"].includes(status)) return "blocked";
  if (["UNKNOWN", "INCOMPLETE", "NO_HISTORY"].includes(status)) return "unknown";
  return "neutral";
}

function statusLabel(status: string) {
  return statusLabels[status] ?? status.replaceAll("_", " ");
}

function EvidenceContent({ item }: { item: Requirement | RequirementReason }) {
  return (
    <div className="evidence-list">
      {item.evidence.length === 0 ? (
        <p>No hay evidencia archivada suficiente para esta conclusión. El estado permanece visible como por verificar.</p>
      ) : (
        item.evidence.map((evidence) => (
          <article className="evidence-item" key={evidence.reference}>
            <strong>{evidence.source_title}</strong>
            <span>{evidence.locator}{evidence.page ? ` · página ${evidence.page}` : ""}</span>
            {evidence.excerpt ? <p>{evidence.excerpt}</p> : null}
            {evidence.annotation ? <small>{evidence.annotation}</small> : null}
            {evidence.source_url ? (
              <a href={evidence.source_url} target="_blank" rel="noreferrer">
                Abrir referencia externa
              </a>
            ) : null}
          </article>
        ))
      )}
      {item.note ? <p className="evidence-note">{item.note}</p> : null}
      {item.source_url && item.evidence.length === 0 ? (
        <a href={item.source_url} target="_blank" rel="noreferrer">
          Referencia externa declarada
        </a>
      ) : null}
    </div>
  );
}

function Explanation({ item, title }: { item: Requirement | RequirementReason; title: string }) {
  const explanation = `${statusLabel(item.status)} · ${item.explanation_key}.`;
  return (
    <RequirementExplanation
      title={title}
      explanation={explanation}
      evidence={<EvidenceContent item={item} />}
    />
  );
}

function CourseOptions({ title, items, empty }: { title: string; items: CourseOption[]; empty: string }) {
  return (
    <section className="dashboard-section" aria-labelledby={`courses-${title}`}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Decisión académica</p>
          <h2 id={`courses-${title}`}>{title}</h2>
        </div>
        <span className="tag tag-outline">{items.length} cursos</span>
      </div>
      {items.length === 0 ? (
        <UnknownState description={empty} />
      ) : (
        <div className="dashboard-course-grid">
          {items.map((course) => (
            <CourseCard
              key={course.code}
              code={course.code}
              name={course.name}
              credits={course.credits}
              status={toneFor(course.eligibility)}
              statusLabel={statusLabel(course.eligibility)}
              metadata={course.group_codes.join(" · ")}
              action={
                <Link className="small-link" href={course.href}>
                  Abrir curso y requisitos →
                </Link>
              }
            />
          ))}
        </div>
      )}
    </section>
  );
}

function OverviewUnavailable({ failure }: { failure: ApiFailure | null }) {
  const description = failure?.unavailable
    ? "El servicio académico no respondió. Puedes reintentar esta vista cuando la API esté disponible."
    : failure?.problem?.code === "ENROLLMENT_NOT_FOUND"
      ? "No hay una matrícula estudiantil disponible para este usuario. Carga o vincula tu historia para iniciar la auditoría."
      : "La auditoría todavía no tiene datos visibles para esta sesión.";
  return (
    <section className="panel dashboard-empty-panel" aria-labelledby="dashboard-empty-title">
      <EmptyState
        title="Auditoría pendiente de datos"
        description={description}
        action={<Link className="button button-primary" href="/history/import">Cargar historia académica</Link>}
      />
      {failure?.correlationId ? <p className="correlation-note">Código de soporte: {failure.correlationId}</p> : null}
    </section>
  );
}

export function AcademicDashboard({
  overview,
  failure = null,
  compact = false,
}: {
  overview: AcademicOverview | null;
  failure?: ApiFailure | null;
  compact?: boolean;
}) {
  if (!overview) return <OverviewUnavailable failure={failure} />;

  const { audit, enrollment } = overview;
  const overall = audit.overall;
  const missing = overview.mandatory_missing;
  const groups: GroupProgressRow[] = overview.groups.map((group) => ({
    label: group.label,
    completed: group.applied_credits,
    required: group.required_credits,
    status: toneFor(group.status),
  }));

  return (
    <div className="academic-dashboard" data-audit-state={overview.state}>
      <section className="dashboard-intro panel" aria-labelledby="dashboard-title">
        <div>
          <p className="eyebrow accent">Resumen verificable · {enrollment.program_code}</p>
          <h1 id="dashboard-title">Tu avance real, con reglas visibles.</h1>
          <p className="dashboard-subtitle">
            {enrollment.program_name} · Plan {enrollment.plan_code} · Revisión {enrollment.revision_code}
          </p>
        </div>
        <div className="dashboard-state">
          <StatusBadge tone={toneFor(overview.state)} label={statusLabel(overview.state)} />
          <small>{statusLabel(overall.status)} según la auditoría del backend</small>
        </div>
      </section>

      {overview.state === "NO_HISTORY" ? (
        <AuditWarning title="Historia sin cargar">
          Aún no hay intentos ni reconocimientos registrados. Los ceros son un estado de datos, no una conclusión sobre tu trayectoria.
          <Link className="small-link" href="/history/import"> Cargar historia →</Link>
        </AuditWarning>
      ) : null}

      {overview.unknowns.length > 0 ? (
        <section className="dashboard-alert-stack" aria-labelledby="unknown-title">
          <h2 id="unknown-title" className="sr-only">Datos por verificar</h2>
          {overview.unknowns.map((unknown) => (
            <AuditWarning key={`${unknown.kind}-${unknown.code}`} title={`Por verificar · ${unknown.code}`}>
              {unknown.detail}
              <Link className="small-link" href={unknown.href}> Ver detalle →</Link>
            </AuditWarning>
          ))}
        </section>
      ) : null}

      <section className="dashboard-metric-grid" aria-label="Créditos de la auditoría">
        <article className="dashboard-metric panel">
          <p className="metric-label">Créditos aplicados</p>
          <strong>{overall.applied_credits}/{overall.required_credits}</strong>
          <small>Los créditos aplicados cierran requisitos concretos.</small>
        </article>
        <article className="dashboard-metric panel">
          <p className="metric-label">Créditos aprobados</p>
          <strong>{overall.earned_credits}</strong>
          <small>Incluye créditos que pueden permanecer sin aplicar.</small>
        </article>
        <article className="dashboard-metric panel">
          <p className="metric-label">Créditos sin aplicar</p>
          <strong>{overall.unapplied_credits}</strong>
          <small>No se reasignan automáticamente a otra agrupación.</small>
        </article>
      </section>

      <section className="dashboard-progress panel" aria-labelledby="credit-progress-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Avance por créditos</p>
            <h2 id="credit-progress-title">{overall.credit_progress_percent}% de créditos aplicados</h2>
          </div>
          <StatusBadge tone={toneFor(overall.status)} label={statusLabel(overall.status)} />
        </div>
        <div className="progress-meter" aria-label="Avance de créditos aplicado por el backend">
          <div className="progress-meter-heading"><span>Aplicados frente al requisito total</span><span>{overall.applied_credits}/{overall.required_credits}</span></div>
          <div className="progress-track" role="progressbar" aria-label="Avance de créditos aplicados" aria-valuemin={0} aria-valuemax={overall.required_credits} aria-valuenow={overall.applied_credits}>
            <span style={{ width: `${overall.credit_progress_percent}%` }} />
          </div>
        </div>
        <p className="dashboard-disclaimer">Este porcentaje sólo describe créditos aplicados. No significa que el grado esté completo mientras existan obligatorias, requisitos externos o estados UNKNOWN pendientes.</p>
      </section>

      <section className="dashboard-section" aria-labelledby="ledger-title">
        <div className="section-heading">
          <div><p className="eyebrow">Contabilidad auditable</p><h2 id="ledger-title">Aprobados, aplicados y excedentes</h2></div>
          <Link className="small-link" href={overview.links.self}>Abrir auditoría completa →</Link>
        </div>
        <div className="dashboard-ledger-grid">
          <CreditLedger earned={overall.earned_credits} applied={overall.applied_credits} unapplied={overall.unapplied_credits} />
          <div className="traceability-card">
            <strong>Resultado reproducible</strong>
            <span>Motor: {audit.metadata.engine_version ?? "no disponible"}</span>
            <span>Hash del resultado: {audit.metadata.result_hash ?? "vista previa"}</span>
            <span>Revisión: {audit.metadata.revision_hash}</span>
          </div>
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="components-title">
        <div className="section-heading"><div><p className="eyebrow">Deuda curricular</p><h2 id="components-title">Progreso por componente</h2></div></div>
        <div className="dashboard-component-grid">
          {overview.components.map((component) => (
            <ComponentProgressCard
              key={component.code}
              label={component.label}
              value={component.applied_credits}
              required={component.required_credits}
              progressPercent={component.progress_percent}
              tone={toneFor(component.status)}
            />
          ))}
        </div>
      </section>

      <section className="dashboard-section" aria-labelledby="groups-title">
        <div className="section-heading"><div><p className="eyebrow">Detalle de requisitos</p><h2 id="groups-title">Progreso por agrupación</h2></div></div>
        <GroupProgressTable rows={groups} />
        <div className="dashboard-missing-grid">
          <div>
            <h3>Obligatorias faltantes</h3>
            {missing.length === 0 ? <p className="muted-copy">No hay obligatorias faltantes según la auditoría.</p> : (
              <ul className="dashboard-link-list">{missing.map((course) => <li key={course.code}><Link href={course.href}>{course.code} · {course.name}</Link></li>)}</ul>
            )}
          </div>
          <div>
            <h3>Próximos desbloqueos</h3>
            {overview.next_unlocks.length === 0 ? <p className="muted-copy">No hay un desbloqueo publicado para mostrar.</p> : (
              <ul className="dashboard-link-list">{overview.next_unlocks.slice(0, compact ? 3 : 8).map((course) => <li key={course.code}><Link href={course.href}>{course.code} · {course.name}</Link><StatusBadge tone={toneFor(course.status)} label={statusLabel(course.status)} /></li>)}</ul>
            )}
          </div>
        </div>
      </section>

      {!compact ? <CourseOptions title="Qué puedes cursar" items={overview.eligible_courses} empty="El backend no identificó cursos elegibles con reglas verificables para este contexto." /> : null}

      {!compact ? (
        <section className="dashboard-section" aria-labelledby="blocked-title">
          <div className="section-heading"><div><p className="eyebrow">Bloqueos explicables</p><h2 id="blocked-title">Cursos bloqueados o por verificar</h2></div></div>
          {overview.blocked_courses.length === 0 && overview.unknown_courses.length === 0 ? <p className="muted-copy">No hay cursos bloqueados o ambiguos en el read model.</p> : (
            <div className="dashboard-reason-grid">
              {[...overview.blocked_courses, ...overview.unknown_courses].slice(0, 12).map((course) => (
                <article className="reason-card panel" key={course.code}>
                  <div className="course-card-header"><div><span className="course-code-label">{course.code}</span><h3>{course.name}</h3></div><StatusBadge tone={toneFor(course.eligibility)} label={statusLabel(course.eligibility)} /></div>
                  {course.reasons.map((reason) => <Explanation key={reason.code} item={reason} title={reason.code} />)}
                  <Link className="small-link" href={course.href}>Abrir curso →</Link>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {!compact ? (
        <section className="dashboard-section" aria-labelledby="graduation-title">
          <div className="section-heading"><div><p className="eyebrow">Requisitos de grado</p><h2 id="graduation-title">Requisitos externos y evidencia</h2></div></div>
          {overview.external_graduation_requirements.length === 0 ? <p className="muted-copy">No hay requisitos externos publicados en esta revisión.</p> : (
            <div className="dashboard-requirement-grid">
              {overview.external_graduation_requirements.map((requirement) => (
                <article className="requirement-card panel" key={requirement.code}>
                  <div className="course-card-header"><span className="course-code-label">{requirement.code}</span><StatusBadge tone={toneFor(requirement.status)} label={statusLabel(requirement.status)} /></div>
                  <Explanation item={requirement} title={requirement.code} />
                  <Link className="small-link" href={requirement.href}>Abrir requisito →</Link>
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {overview.warnings.length > 0 ? (
        <section className="dashboard-section" aria-labelledby="warnings-title">
          <div className="section-heading"><div><p className="eyebrow">Trazabilidad</p><h2 id="warnings-title">Advertencias de la auditoría</h2></div></div>
          <ul className="dashboard-warning-list">{overview.warnings.map((warning) => <li key={warning.code}><StatusBadge tone={warning.severity === "ERROR" ? "blocked" : "unknown"} label={warning.title} /><span>{warning.detail}</span><Link href={warning.href}>Ver →</Link></li>)}</ul>
        </section>
      ) : null}
    </div>
  );
}

export function DashboardErrorNote({ children }: { children: ReactNode }) {
  return <p className="correlation-note">{children}</p>;
}
