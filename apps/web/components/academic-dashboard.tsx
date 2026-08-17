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
  const remainingCredits = Math.max(0, overall.required_credits - overall.applied_credits);
  const firstEligible = overview.eligible_courses.slice(0, 6);
  const firstMissing = missing.slice(0, 6);

  return (
    <div className="academic-dashboard" data-audit-state={overview.state}>
      <section className="audit-decision-hero" aria-labelledby="dashboard-title">
        <div className="audit-decision-copy">
          <p className="eyebrow accent">Auditoría de grado</p>
          <h1 id="dashboard-title">{remainingCredits} créditos por completar</h1>
          <span>{missing.length} obligatorias pendientes · {overview.unknowns.length} datos por verificar</span>
        </div>
        <div className="audit-progress-orbit" role="progressbar" aria-label="Créditos aplicados" aria-valuemin={0} aria-valuemax={overall.required_credits} aria-valuenow={overall.applied_credits}>
          <strong>{overall.credit_progress_percent}%</strong>
          <span>{overall.applied_credits} de {overall.required_credits}</span>
        </div>
        <div className="audit-hero-actions"><Link className="button button-primary" href="/curriculum">Abrir malla</Link><Link className="button button-secondary" href="/planner">Planear</Link></div>
      </section>

      {overview.state === "NO_HISTORY" ? (
        <AuditWarning title="Historia sin cargar">
          Aún no hay intentos ni reconocimientos registrados. Los ceros son un estado de datos, no una conclusión sobre tu trayectoria.
          <Link className="small-link" href="/history/import"> Cargar historia →</Link>
        </AuditWarning>
      ) : null}

      <section className="audit-next-grid" aria-label="Tus siguientes decisiones">
        <article className="audit-next-card audit-next-primary">
          <p className="eyebrow">Puedes matricular</p>
          <strong>{overview.eligible_courses.length}</strong>
          <span>asignaturas cumplen hoy sus prerrequisitos</span>
          <ul>{firstEligible.map((course) => <li key={course.code}><Link href={course.href}><b>{course.code}</b>{course.name}</Link></li>)}</ul>
          <Link className="small-link" href="/curriculum?status=ELIGIBLE">Ver todas en la malla →</Link>
        </article>
        <article className="audit-next-card">
          <p className="eyebrow">Obligatorias pendientes</p>
          <strong>{missing.length}</strong>
          <span>siguen siendo parte de tu ruta base</span>
          <ul>{firstMissing.map((course) => <li key={course.code}><Link href={course.href}><b>{course.code}</b>{course.name}</Link></li>)}</ul>
          {missing.length > firstMissing.length ? <details><summary>Ver las {missing.length} obligatorias pendientes</summary><ul>{missing.map((course) => <li key={course.code}><Link href={course.href}><b>{course.code}</b>{course.name}</Link></li>)}</ul></details> : null}
        </article>
        <article className="audit-next-card audit-next-review">
          <p className="eyebrow">Necesitan confirmación</p>
          <strong>{overview.unknowns.length}</strong>
          <span>datos no se asumirán hasta contar con evidencia</span>
          {overview.unknowns.length ? <details><summary>Revisar datos pendientes</summary><ul>{overview.unknowns.map((unknown) => <li key={`${unknown.kind}-${unknown.code}`}><span>{unknown.detail}</span><Link href={unknown.href}>Abrir</Link></li>)}</ul></details> : <p>No hay ambigüedades pendientes.</p>}
        </article>
      </section>

      <section className="dashboard-section audit-components" aria-labelledby="components-title">
        <div className="section-heading">
          <div><p className="eyebrow">Dónde está la deuda</p><h2 id="components-title">Avance por componente</h2></div>
          <StatusBadge tone={toneFor(overall.status)} label={statusLabel(overall.status)} />
        </div>
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

      {!compact ? <details className="audit-disclosure panel"><summary><span><b>Entender bloqueos y requisitos</b><small>Agrupaciones, cursos bloqueados y requisitos externos</small></span></summary><div className="audit-disclosure-body">
        <section className="dashboard-section" aria-labelledby="groups-title"><div className="section-heading"><div><p className="eyebrow">Detalle curricular</p><h2 id="groups-title">Progreso por agrupación</h2></div></div><GroupProgressTable rows={groups} /></section>
        <section className="dashboard-section" aria-labelledby="blocked-title"><div className="section-heading"><div><p className="eyebrow">Bloqueos explicables</p><h2 id="blocked-title">Por qué todavía no puedes cursar algunas asignaturas</h2></div></div>
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
      </div></details> : null}

      <details className="audit-disclosure panel"><summary><span><b>Cómo se calculó este resultado</b><small>Créditos, versión del motor, evidencia y advertencias</small></span></summary><div className="audit-disclosure-body">
        <div className="dashboard-ledger-grid"><CreditLedger earned={overall.earned_credits} applied={overall.applied_credits} unapplied={overall.unapplied_credits} /><div className="traceability-card"><strong>Resultado reproducible</strong><span>Motor: {audit.metadata.engine_version ?? "no disponible"}</span><span>Hash: {audit.metadata.result_hash ?? "vista previa"}</span><span>Revisión: {audit.metadata.revision_hash}</span></div></div>
        {overview.warnings.length > 0 ? <section className="dashboard-section" aria-labelledby="warnings-title">
          <div className="section-heading"><div><p className="eyebrow">Trazabilidad</p><h2 id="warnings-title">Advertencias de la auditoría</h2></div></div>
          <ul className="dashboard-warning-list">{overview.warnings.map((warning) => <li key={warning.code}><StatusBadge tone={warning.severity === "ERROR" ? "blocked" : "unknown"} label={warning.title} /><span>{warning.detail}</span><Link href={warning.href}>Ver →</Link></li>)}</ul>
        </section> : null}
        <p className="dashboard-disclaimer">{enrollment.program_name} · Plan {enrollment.plan_code} · Revisión {enrollment.revision_code}. Los créditos aplicados cierran requisitos concretos; aprobar créditos no certifica por sí solo el grado.</p>
      </div></details>
    </div>
  );
}

export function DashboardErrorNote({ children }: { children: ReactNode }) {
  return <p className="correlation-note">{children}</p>;
}
