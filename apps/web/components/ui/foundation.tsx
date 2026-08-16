import type { ReactNode } from "react";

import { EmptyState } from "./empty-state";
import { ProgressMeter } from "./progress-meter";
import { StatusBadge, type StatusTone } from "./status-badge";

export interface CourseCardProps {
  code: string;
  name: string;
  credits: number;
  status: StatusTone;
  statusLabel?: string;
  metadata?: string;
  action?: ReactNode;
}

export function CourseStatusBadge({ tone, label }: { tone: StatusTone; label?: string }) {
  return <StatusBadge tone={tone} label={label} />;
}

export function CourseCard({ code, name, credits, status, statusLabel, metadata, action }: CourseCardProps) {
  return (
    <article className="course-card panel">
      <div className="course-card-header">
        <span className="course-code-label">{code}</span>
        <CourseStatusBadge tone={status} label={statusLabel} />
      </div>
      <h3>{name}</h3>
      <p className="course-card-meta">{credits} créditos{metadata ? ` · ${metadata}` : ""}</p>
      {action ? <div className="course-card-action">{action}</div> : null}
    </article>
  );
}

export function RequirementChip({ label, tone = "neutral" }: { label: string; tone?: StatusTone }) {
  return <span className={`requirement-chip requirement-chip-${tone}`}>{label}</span>;
}

export interface CreditLedgerProps {
  earned: number;
  applied: number;
  unapplied: number;
  unit?: string;
}

export function CreditLedger({ earned, applied, unapplied, unit = "créditos" }: CreditLedgerProps) {
  const rows = [
    ["Aprobados", earned, "passed"],
    ["Aplicados", applied, "eligible"],
    ["Sin aplicar", unapplied, "unknown"],
  ] as const;
  return (
    <dl className="credit-ledger">
      {rows.map(([label, value, tone]) => (
        <div className="credit-ledger-row" key={label}>
          <dt><span className={`ledger-dot ledger-dot-${tone}`} aria-hidden="true" />{label}</dt>
          <dd>{value} <small>{unit}</small></dd>
        </div>
      ))}
    </dl>
  );
}

export function ComponentProgressCard({ label, value, required, tone = "neutral" }: { label: string; value: number; required: number; tone?: StatusTone }) {
  return (
    <article className={`component-progress-card panel component-${tone}`}>
      <div className="component-card-heading"><h3>{label}</h3><span>{value}/{required}</span></div>
      <ProgressMeter value={value} max={required} label={`${label}: progreso`} />
    </article>
  );
}

export interface GroupProgressRow {
  label: string;
  completed: number;
  required: number;
  status: StatusTone;
}

export function GroupProgressTable({ rows }: { rows: GroupProgressRow[] }) {
  return (
    <div className="table-scroll">
      <table className="group-progress-table">
        <caption>Progreso por agrupación</caption>
        <thead><tr><th scope="col">Agrupación</th><th scope="col">Avance</th><th scope="col">Estado</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.label}><th scope="row">{row.label}</th><td>{row.completed}/{row.required}</td><td><StatusBadge tone={row.status} /></td></tr>)}</tbody>
      </table>
    </div>
  );
}

export function EvidencePopover({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="evidence-popover">
      <summary>{title}</summary>
      <div className="evidence-popover-content">{children}</div>
    </details>
  );
}

export function RequirementExplanation({ title, explanation, evidence }: { title: string; explanation: string; evidence?: ReactNode }) {
  return (
    <section className="requirement-explanation" aria-labelledby={`requirement-${title}`}>
      <h3 id={`requirement-${title}`}>{title}</h3>
      <p>{explanation}</p>
      {evidence ? <EvidencePopover title="Ver evidencia">{evidence}</EvidencePopover> : null}
    </section>
  );
}

export function CurriculumGrid({ children, label = "Malla curricular" }: { children: ReactNode; label?: string }) {
  return <section className="curriculum-grid" aria-label={label}>{children}</section>;
}

export interface GraphNode {
  id: string;
  label: string;
  status: StatusTone;
}

export function DependencyGraph({ nodes, description = "Representación textual de dependencias" }: { nodes: GraphNode[]; description?: string }) {
  return (
    <section className="dependency-graph panel" aria-label="Grafo de dependencias">
      <p className="eyebrow">Vista accesible</p>
      <h2>Dependencias</h2>
      <p className="graph-description">{description}</p>
      <ol className="graph-node-list">{nodes.map((node) => <li key={node.id}><span className="graph-node-id">{node.id}</span><span>{node.label}</span><StatusBadge tone={node.status} /></li>)}</ol>
    </section>
  );
}

export function GraphLegend({ items }: { items: Array<{ label: string; tone: StatusTone }> }) {
  return <ul className="graph-legend" aria-label="Leyenda del grafo">{items.map((item) => <li key={item.label}><StatusBadge tone={item.tone} label={item.label} /></li>)}</ul>;
}

export function PlannerTermColumn({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return <section className="planner-term-column panel" aria-labelledby={`term-${title}`}><h3 id={`term-${title}`}>{title}</h3>{subtitle ? <p>{subtitle}</p> : null}<div>{children}</div></section>;
}

export function ScenarioCompare({ leftLabel, rightLabel, left, right }: { leftLabel: string; rightLabel: string; left: ReactNode; right: ReactNode }) {
  return <div className="scenario-compare"><section className="panel"><p className="eyebrow">{leftLabel}</p>{left}</section><section className="panel"><p className="eyebrow">{rightLabel}</p>{right}</section></div>;
}

export function OfferingBadge({ label, tone = "eligible" }: { label: string; tone?: StatusTone }) {
  return <StatusBadge tone={tone} label={label} />;
}

export function ScheduleGrid({ slots }: { slots: Array<{ label: string; value: string }> }) {
  return <dl className="schedule-grid">{slots.map((slot) => <div key={slot.label}><dt>{slot.label}</dt><dd>{slot.value}</dd></div>)}</dl>;
}

export function AuditWarning({ title, children }: { title: string; children: ReactNode }) {
  return <div className="audit-warning" role="alert"><StatusBadge tone="unknown" label={title} /><p>{children}</p></div>;
}

export function UnknownState({ title = "Estado por verificar", description }: { title?: string; description: string }) {
  return <EmptyState tone="unknown" title={title} description={description} />;
}

export function SourceViewer({ title, source, children }: { title: string; source: string; children: ReactNode }) {
  return <section className="source-viewer panel" aria-labelledby={`source-${title}`}><p className="eyebrow">{source}</p><h2 id={`source-${title}`}>{title}</h2><div className="source-viewer-body">{children}</div></section>;
}

export function SemanticDiff({ changes }: { changes: Array<{ label: string; detail: string; tone?: StatusTone }> }) {
  return <ul className="semantic-diff" aria-label="Cambios semánticos">{changes.map((change) => <li key={`${change.label}-${change.detail}`}><StatusBadge tone={change.tone ?? "neutral"} label={change.label} /><span>{change.detail}</span></li>)}</ul>;
}
