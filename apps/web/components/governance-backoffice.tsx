"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  applyGovernanceCandidates,
  getGovernanceProposal,
  linkGovernanceRequirementEvidence,
  previewGovernanceCandidates,
  publishGovernanceProposal,
  problemMessage,
  reviewGovernanceCandidate,
  reviewGovernanceProposal,
  submitGovernanceProposal,
  type ApiFailure,
  type GovernanceProposal,
  type SourceInbox,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { EmptyState } from "./ui/empty-state";
import { StatusBadge } from "./ui/status-badge";

type ProposalSummary = SourceInbox["proposals"][number];
type Candidate = GovernanceProposal["candidates"][number];
type SemanticDiff = {
  added: Record<string, unknown[]>;
  removed: Record<string, unknown[]>;
  changed: Array<{ entity: string; key: string; before: unknown; after: unknown }>;
};
type GovernanceAuditEvent = {
  id: string;
  action: string;
  object_type: string;
  object_id: string;
  actor: string | null;
  created_at: string;
};
type PublicationImpact = {
  id: string;
  enrollment_id: string;
  previous_revision_id: string;
  previous_audit_run_id: string | null;
  previous_audit_result_hash: string;
  impact_status: string;
  recompute_job_key: string;
  requires_revision_decision: boolean;
};
type PublicationEvent = {
  id: string;
  event_type: string;
  revision_id: string;
  superseded_revision_id: string | null;
  impact_summary: {
    changed_courses: number;
    changed_groups: number;
    changed_requirements: number;
    affected_enrollments: number;
    affected_audits: number;
    old_audits_reproducible: boolean;
  };
  recompute_plan: { status: string; jobs: Array<{ job_key: string; enrollment_id: string }> };
  notification_plan: { status: string; recipient_count: number; after_commit_only: boolean };
  enrollment_impacts: PublicationImpact[];
};

function statusTone(status: string): "passed" | "in-progress" | "blocked" | "unknown" | "neutral" {
  if (["PUBLISHED", "APPROVED", "ACCEPTED"].includes(status)) return "passed";
  if (["IN_REVIEW", "PENDING", "DRAFT"].includes(status)) return "in-progress";
  if (["REJECTED", "REMOVED"].includes(status)) return "blocked";
  if (["UNKNOWN", "DISPUTED", "INFERRED_PENDING_REVIEW"].includes(status)) return "unknown";
  return "neutral";
}

function diffCount(proposal: GovernanceProposal) {
  const diff = proposal.semantic_diff as SemanticDiff;
  const added = Object.values(diff.added ?? {}).reduce((total, rows) => total + (Array.isArray(rows) ? rows.length : 0), 0);
  const removed = Object.values(diff.removed ?? {}).reduce((total, rows) => total + (Array.isArray(rows) ? rows.length : 0), 0);
  const changed = Array.isArray(diff.changed) ? diff.changed.length : 0;
  return { added, removed, changed };
}

function failureText(failure: ApiFailure | null) {
  return failure ? problemMessage(failure.problem, failure.unavailable ? "La API no está disponible." : "No se pudo completar la operación.") : null;
}

function publicationEvent(proposal: GovernanceProposal): PublicationEvent | null {
  const publication = proposal.publication as { event?: PublicationEvent } | null;
  return publication?.event ?? null;
}

function CandidateRow({
  candidate,
  selected,
  onToggle,
  onReview,
  busy,
}: {
  candidate: Candidate;
  selected: boolean;
  onToggle: () => void;
  onReview: (candidate: Candidate, status: "ACCEPTED" | "REJECTED") => void;
  busy: boolean;
}) {
  return (
    <tr>
      <td>
        <input type="checkbox" checked={selected} onChange={onToggle} aria-label={`Seleccionar candidato ${candidate.entity} ${candidate.entity_key}`} />
      </td>
      <td><code>{candidate.entity}:{candidate.entity_key}</code></td>
      <td>{candidate.operation}</td>
      <td><StatusBadge tone={statusTone(candidate.status)} label={candidate.status} /></td>
      <td>{candidate.evidence.length ? `${candidate.evidence.length} evidencia(s)` : "Sin evidencia enlazada"}</td>
      <td>
        <div className="governance-row-actions">
          <button className="button button-quiet" type="button" disabled={busy} onClick={() => onReview(candidate, "ACCEPTED")}>Aceptar</button>
          <button className="button button-quiet" type="button" disabled={busy} onClick={() => onReview(candidate, "REJECTED")}>Rechazar</button>
        </div>
      </td>
    </tr>
  );
}

export function GovernanceBackoffice({
  initialInbox,
  initialFailure,
  initialProposal,
  initialProposalEtag,
  initialProposalFailure,
  roles,
}: {
  initialInbox: SourceInbox | null;
  initialFailure: ApiFailure | null;
  initialProposal: GovernanceProposal | null;
  initialProposalEtag: string | null;
  initialProposalFailure: ApiFailure | null;
  roles: string[];
}) {
  const [inbox] = useState(initialInbox);
  const [selectedId, setSelectedId] = useState<string | null>(initialInbox?.proposals[0]?.id ?? null);
  const [proposal, setProposal] = useState<GovernanceProposal | null>(initialProposal);
  const [etag, setEtag] = useState<string | null>(initialProposalEtag ?? (initialInbox?.proposals[0]?.version ? `"${initialInbox.proposals[0].version}"` : null));
  const [failure, setFailure] = useState<ApiFailure | null>(initialProposalFailure ?? initialFailure);
  const [busy, setBusy] = useState(false);
  const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
  const [bulkPreview, setBulkPreview] = useState<{ token: string; total: number; allowed: number; blocked: number } | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState(() => failureText(initialProposalFailure ?? initialFailure) ?? "");

  const canEdit = roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role));
  const canReview = roles.some((role) => ["REVIEWER", "ADMIN"].includes(role));
  const selectedRequirement = useMemo(
    () => proposal?.requirements.find((requirement) => requirement.id === (selectedRequirementId ?? proposal.requirements[0]?.id)) ?? null,
    [proposal, selectedRequirementId],
  );
  const currentDiff = proposal ? (proposal.semantic_diff as SemanticDiff) : null;
  const auditEvents = (proposal?.audit_events ?? []) as unknown as GovernanceAuditEvent[];

  async function loadProposal(id: string) {
    setBusy(true);
    setAnnouncement("Cargando la propuesta seleccionada.");
    const result = await getGovernanceProposal(id);
    setBusy(false);
    setFailure(result.failure);
    if (result.data) {
      setProposal(result.data);
      setEtag(result.etag ?? `"${result.data.version}"`);
      setSelectedCandidates([]);
      setBulkPreview(null);
      setAnnouncement(`Propuesta ${result.data.title} cargada.`);
    } else {
      setAnnouncement(failureText(result.failure) ?? "No se pudo cargar la propuesta seleccionada.");
    }
  }

  async function refresh() {
    if (selectedId) await loadProposal(selectedId);
  }

  async function mutate(action: () => Promise<{ data: GovernanceProposal | null; failure: ApiFailure | null }>) {
    setBusy(true);
    const result = await action();
    setBusy(false);
    setFailure(result.failure);
    if (result.data) {
      setProposal(result.data);
      setEtag(`"${result.data.version}"`);
      setBulkPreview(null);
      setSelectedCandidates([]);
      setAnnouncement(`La propuesta ahora está en estado ${result.data.status}.`);
    } else if (result.failure?.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT") {
      setFailure(result.failure);
      setAnnouncement(failureText(result.failure) ?? "Conflicto de concurrencia. Recarga la propuesta actual.");
    } else if (result.failure) {
      setAnnouncement(failureText(result.failure) ?? "No se pudo completar la operación editorial.");
    }
  }

  async function reviewCandidate(candidate: Candidate, status: "ACCEPTED" | "REJECTED") {
    if (!proposal) return;
    setBusy(true);
    const result = await reviewGovernanceCandidate(proposal.id, candidate.id, {
      status,
      epistemic_status: candidate.epistemic_status,
      note: candidate.note,
      evidence_ids: candidate.evidence.map((evidence) => evidence.id),
    }, { ifMatch: candidate.version });
    setBusy(false);
    setFailure(result.failure);
    if (result.failure) {
      setAnnouncement(failureText(result.failure) ?? "No se pudo revisar el candidato.");
      return;
    }
    setAnnouncement(`Candidato ${candidate.entity_key} marcado como ${status}.`);
    await refresh();
  }

  async function previewBulk() {
    if (!proposal || !selectedCandidates.length) return;
    setBusy(true);
    const result = await previewGovernanceCandidates(proposal.id, {
      candidate_ids: selectedCandidates,
      status: "ACCEPTED",
      epistemic_status: "INFERRED_PENDING_REVIEW",
      note: "",
      evidence_ids: [],
      preview_token: null,
    });
    setBusy(false);
    setFailure(result.failure);
    if (result.data) {
      setBulkPreview({ token: result.data.preview_token, total: result.data.total, allowed: result.data.allowed, blocked: result.data.blocked.length });
      setAnnouncement(`Previsualización lista: ${result.data.allowed} candidatos aplicables y ${result.data.blocked.length} bloqueados.`);
    } else {
      setAnnouncement(failureText(result.failure) ?? "No se pudo previsualizar la aceptación masiva.");
    }
  }

  async function applyBulk() {
    if (!proposal || !bulkPreview || !etag) return;
    await mutate(() => applyGovernanceCandidates(proposal.id, {
      candidate_ids: selectedCandidates,
      status: "ACCEPTED",
      epistemic_status: "INFERRED_PENDING_REVIEW",
      note: "Aceptación masiva confirmada después de previsualización.",
      evidence_ids: [],
      preview_token: bulkPreview.token,
    }, { ifMatch: etag }));
  }

  async function linkSelectedRequirementEvidence() {
    if (!selectedRequirement) return;
    setBusy(true);
    const result = await linkGovernanceRequirementEvidence(
      selectedRequirement.id,
      selectedRequirement.evidence.map((item) => item.id),
      { ifMatch: selectedRequirement.version },
    );
    setBusy(false);
    setFailure(result.failure);
    if (result.failure) {
      setAnnouncement(failureText(result.failure) ?? "No se pudieron guardar los vínculos de evidencia.");
    } else {
      setAnnouncement("Vínculos de evidencia guardados.");
      await refresh();
    }
  }

  if (!canEdit && !initialFailure) {
    return <div className="page-shell"><section className="panel module-panel"><EmptyState title="Acceso editorial requerido" description="La bandeja de fuentes y publicación sólo está disponible para editores, revisores y administradores con alcance institucional." action={<Link className="button button-primary" href="/">Volver al inicio</Link>} /></section></div>;
  }

  if (!inbox) {
    return <div className="page-shell"><section className="panel module-panel"><p className="eyebrow accent">Bandeja de fuentes</p><h1>La bandeja editorial no está disponible</h1><Alert tone="error">{failureText(failure) ?? "No se pudo cargar la procedencia normativa."}</Alert></section></div>;
  }

  return (
    <div className="page-shell governance-page">
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true" data-testid="governance-live-region">{announcement}</p>
      <div className="governance-back-link"><Link className="text-link" href="/">← Volver al resumen</Link></div>
      <section className="panel governance-hero">
        <div>
          <p className="eyebrow accent">Bandeja de fuentes · gobernanza curricular</p>
          <h1>Gobierna antes de publicar.</h1>
          <p>Fuentes archivadas, candidatos extraídos, reglas explicables y revisiones inmutables viven en una misma cadena auditable.</p>
        </div>
        <div className="governance-hero-facts" aria-label="Resumen de la bandeja">
          <span><strong>{inbox.documents.length}</strong> documentos</span>
          <span><strong>{inbox.snapshots.length}</strong> snapshots</span>
          <span><strong>{inbox.proposals.length}</strong> propuestas</span>
        </div>
      </section>

      {failure ? <Alert tone={failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? "error" : "info"}><strong>{failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? "Conflicto de concurrencia." : "Estado editorial."}</strong> {failureText(failure)} {failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? <button className="button button-quiet" type="button" onClick={() => selectedId && void loadProposal(selectedId)}>Recargar versión actual</button> : null}</Alert> : null}

      <section className="governance-workflow panel" aria-labelledby="governance-workflow-title">
        <div className="section-heading"><div><p className="eyebrow">Cadena de procedencia</p><h2 id="governance-workflow-title">Ningún salto directo a VERIFIED o PUBLISHED</h2></div><span className="tag tag-outline">Control editorial</span></div>
        <ol className="governance-workflow-list">{inbox.workflow.map((stage, index) => <li key={stage}><span>{String(index + 1).padStart(2, "0")}</span><strong>{stage}</strong></li>)}</ol>
      </section>

      <div className="governance-layout">
        <aside className="panel governance-sidebar" aria-labelledby="governance-queue-title">
          <div className="section-heading"><div><p className="eyebrow">Cola de revisión</p><h2 id="governance-queue-title">Propuestas</h2></div><span className="tag tag-outline">{inbox.proposals.length}</span></div>
          <ul className="governance-proposal-list">
            {inbox.proposals.map((item: ProposalSummary) => <li key={item.id}><button className={selectedId === item.id ? "governance-proposal-card selected" : "governance-proposal-card"} type="button" onClick={() => { setSelectedId(item.id); void loadProposal(item.id); }}><span className="governance-card-top"><code>{item.candidate_revision_code}</code><StatusBadge tone={statusTone(item.status)} label={item.status} /></span><strong>{item.title}</strong><small>{item.pending_candidates} candidatos pendientes · {item.semantic_has_changes ? "con cambios semánticos" : "sin cambios semánticos"}</small></button></li>)}
          </ul>
          <div className="governance-source-list"><h3>Snapshots recientes</h3>{inbox.snapshots.slice(0, 5).map((snapshot) => <article key={snapshot.id}><code>{snapshot.sha256.slice(0, 12)}…</code><p>{snapshot.document_title}</p><small>{snapshot.evidence_count} evidencias · {snapshot.mime_type}</small></article>)}</div>
        </aside>

        <section className="governance-main" aria-label="Detalle de la propuesta">
          {!proposal || busy ? <section className="panel governance-loading"><p className="eyebrow">Propuesta</p><h2>{busy ? "Cargando estado auditable…" : "Selecciona una propuesta"}</h2></section> : <>
            <section className="panel governance-detail-header">
              <div><p className="eyebrow accent">Revisión en borrador · {proposal.candidate_revision.plan_code}</p><h2>{proposal.title}</h2><p>{proposal.rationale}</p></div>
              <div className="governance-detail-meta"><StatusBadge tone={statusTone(proposal.status)} label={proposal.status} /><span>Versión <code>{proposal.version}</code></span><span>Hash <code>{proposal.content_fingerprint.slice(0, 16)}…</code></span></div>
            </section>

            <section className="panel governance-actions" aria-labelledby="governance-actions-title">
              <div className="section-heading"><div><p className="eyebrow">Workflow controlado</p><h2 id="governance-actions-title">Acciones con separación de funciones</h2></div></div>
              <div className="governance-action-grid">
                {proposal.status === "DRAFT" ? <button className="button button-primary" type="button" disabled={busy || !etag} onClick={() => mutate(() => submitGovernanceProposal(proposal.id, {}, { ifMatch: etag ?? "" }))}>Enviar a revisión</button> : null}
                {canReview && proposal.status === "IN_REVIEW" ? <><button className="button button-primary" type="button" disabled={busy || !etag} onClick={() => mutate(() => reviewGovernanceProposal(proposal.id, { decision: "APPROVE", comment: reviewComment }, { ifMatch: etag ?? "" }))}>Aprobar revisión</button><button className="button button-secondary" type="button" disabled={busy || !etag} onClick={() => mutate(() => reviewGovernanceProposal(proposal.id, { decision: "REQUEST_CHANGES", comment: reviewComment }, { ifMatch: etag ?? "" }))}>Solicitar cambios</button><button className="button button-secondary" type="button" disabled={busy || !etag} onClick={() => mutate(() => reviewGovernanceProposal(proposal.id, { decision: "REJECT", comment: reviewComment }, { ifMatch: etag ?? "" }))}>Rechazar</button></> : null}
                {canReview && proposal.status === "APPROVED" ? <div className="governance-publish-control"><label htmlFor="publication-confirmation">Confirmación explícita de publicación</label><textarea id="publication-confirmation" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder="He revisado el diff, la validación, el impacto y la evidencia." /><button className="button button-primary" type="button" disabled={busy || !etag || confirmation.trim().length < 20} onClick={() => mutate(() => publishGovernanceProposal(proposal.id, confirmation, { ifMatch: etag ?? "" }))}>Publicar revisión aprobada</button></div> : null}
              </div>
              {proposal.status === "IN_REVIEW" ? <label className="field-group governance-comment"><span>Comentario de revisión</span><textarea value={reviewComment} onChange={(event) => setReviewComment(event.target.value)} placeholder="Qué evidencia o ajuste debe quedar trazable…" /></label> : null}
              {proposal.status === "PUBLISHED" || proposal.publication ? <Alert tone="success">Esta revisión tiene recibo de publicación y no se edita directamente. Cualquier cambio debe crear una nueva revisión.</Alert> : null}
            </section>

            <section className="governance-metric-grid" aria-label="Validación e impacto">
              <article className="panel governance-metric"><span>Validación</span><strong>{proposal.validation_report.ok ? "VÁLIDA" : "BLOQUEADA"}</strong><small>{proposal.validation_report.errors.length} errores · {proposal.validation_report.unknowns.length} unknowns</small></article>
              <article className="panel governance-metric"><span>Diff semántico</span><strong>{diffCount(proposal).changed + diffCount(proposal).added + diffCount(proposal).removed}</strong><small>{diffCount(proposal).added} añadidos · {diffCount(proposal).removed} retirados · {diffCount(proposal).changed} cambios</small></article>
              <article className="panel governance-metric"><span>Impacto</span><strong>{proposal.impact_analysis.students_potentially_affected}</strong><small>estudiantes potencialmente afectados · {proposal.impact_analysis.audits_affected} auditorías</small></article>
            </section>

            {publicationEvent(proposal) ? <section className="panel governance-section governance-publication-impact" aria-labelledby="governance-publication-impact-title"><div className="section-heading"><div><p className="eyebrow">Evento de publicación</p><h2 id="governance-publication-impact-title">Impacto materializado después de publicar</h2><p>La revisión anterior conserva sus auditorías; cada matrícula afectada tiene un plan de recomputación que requiere decisión de cohorte.</p></div><StatusBadge tone="passed" label="INMUTABLE" /></div><div className="governance-impact-summary">{(() => { const event = publicationEvent(proposal); if (!event) return null; return <><article><strong>{event.impact_summary.affected_enrollments}</strong><span>matrículas identificadas</span></article><article><strong>{event.impact_summary.affected_audits}</strong><span>auditorías preservadas</span></article><article><strong>{event.impact_summary.changed_courses + event.impact_summary.changed_groups + event.impact_summary.changed_requirements}</strong><span>familias semánticas afectadas</span></article><article><strong>{event.notification_plan.recipient_count}</strong><span>notificaciones encoladas tras commit</span></article></>; })()}</div><div className="governance-impact-list"><h3>Plan de recomputación</h3>{(() => { const event = publicationEvent(proposal); if (!event) return null; return event.enrollment_impacts.length ? <ul>{event.enrollment_impacts.slice(0, 20).map((impact) => <li key={impact.id}><strong>{impact.impact_status}</strong><code>{impact.recompute_job_key}</code><small>{impact.previous_audit_run_id ? `Auditoría anterior ${impact.previous_audit_result_hash.slice(0, 16)}…` : "Sin auditoría previa persistida"} · decisión de revisión requerida</small></li>)}</ul> : <p className="muted-copy">No hay matrículas con la revisión anterior; el plan de recomputación no requiere trabajos.</p>; })()}</div></section> : null}

            <section className="panel governance-section" aria-labelledby="governance-diff-title"><div className="section-heading"><div><p className="eyebrow">Semantic diff</p><h2 id="governance-diff-title">Cambios que el revisor debe entender</h2></div></div><div className="governance-diff-grid">{Object.entries(currentDiff?.added ?? {}).map(([entity, rows]) => <div key={`add-${entity}`} className="governance-diff-card governance-diff-added"><strong>{entity} añadidos</strong><span>{Array.isArray(rows) ? rows.length : 0}</span></div>)}{Object.entries(currentDiff?.removed ?? {}).map(([entity, rows]) => <div key={`remove-${entity}`} className="governance-diff-card governance-diff-removed"><strong>{entity} retirados</strong><span>{Array.isArray(rows) ? rows.length : 0}</span></div>)}{(currentDiff?.changed ?? []).slice(0, 12).map((item, index) => <details className="governance-diff-change" key={`${item.entity}-${item.key}-${index}`}><summary><strong>{item.entity}</strong> · {item.key}</summary><div><pre>{JSON.stringify({ before: item.before, after: item.after }, null, 2)}</pre></div></details>)}</div></section>

            <section className="panel governance-section" aria-labelledby="governance-candidates-title"><div className="section-heading"><div><p className="eyebrow">Candidatos de extracción</p><h2 id="governance-candidates-title">Revisión de afirmaciones extraídas</h2><p>La selección masiva siempre requiere una previsualización sin escrituras antes de aplicar.</p></div><div className="governance-row-actions"><button className="button button-secondary" type="button" disabled={!selectedCandidates.length || busy} onClick={() => void previewBulk()}>Previsualizar aceptación masiva</button>{bulkPreview ? <button className="button button-primary" type="button" disabled={busy || bulkPreview.blocked > 0} onClick={() => void applyBulk()}>Aplicar preview ({bulkPreview.allowed})</button> : null}</div></div>{bulkPreview ? <Alert tone={bulkPreview.blocked ? "error" : "success"}><strong>Preview sin escrituras:</strong> {bulkPreview.total} seleccionados, {bulkPreview.allowed} aplicables, {bulkPreview.blocked} bloqueados.</Alert> : null}<div className="table-scroll"><table className="governance-table"><caption>Candidatos extraídos de {proposal.source_snapshot.sha256.slice(0, 16)}…</caption><thead><tr><th scope="col">Seleccionar</th><th scope="col">Entidad</th><th scope="col">Operación</th><th scope="col">Estado</th><th scope="col">Evidencia</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead><tbody>{proposal.candidates.slice(0, 80).map((candidate) => <CandidateRow key={candidate.id} candidate={candidate} selected={selectedCandidates.includes(candidate.id)} onToggle={() => setSelectedCandidates((current) => current.includes(candidate.id) ? current.filter((id) => id !== candidate.id) : [...current, candidate.id])} onReview={(item, status) => void reviewCandidate(item, status)} busy={busy} />)}</tbody></table></div></section>

            <section className="panel governance-section" aria-labelledby="governance-rule-title"><div className="section-heading"><div><p className="eyebrow">Inspector de reglas</p><h2 id="governance-rule-title">AST legible + explicación humana + evidencia</h2></div><label className="field-group"><span>Regla</span><select value={selectedRequirement?.id ?? ""} onChange={(event) => setSelectedRequirementId(event.target.value)}>{proposal.requirements.slice(0, 80).map((requirement) => <option key={requirement.id} value={requirement.id}>{requirement.code} · {requirement.epistemic_status}</option>)}</select></label></div>{selectedRequirement ? <div className="governance-rule-grid"><div className="governance-rule-copy"><StatusBadge tone={statusTone(selectedRequirement.epistemic_status)} label={selectedRequirement.epistemic_status} /><h3>{selectedRequirement.code}</h3><p>{selectedRequirement.human_explanation}</p><p className="muted-copy">{selectedRequirement.purpose} · {selectedRequirement.ast_schema_version} · {selectedRequirement.ast_hash.slice(0, 16)}…</p><button className="button button-secondary" type="button" disabled={busy || !selectedRequirement.evidence.length} onClick={() => void linkSelectedRequirementEvidence()}>Guardar vínculos de evidencia</button></div><div><h3>AST serializado</h3><pre className="governance-ast">{JSON.stringify(selectedRequirement.ast, null, 2)}</pre></div><div><h3>Evidencia vinculada</h3>{selectedRequirement.evidence.length ? <ul className="governance-evidence-list">{selectedRequirement.evidence.map((evidence) => <li key={evidence.id}><strong>{evidence.locator}</strong><span>{evidence.excerpt}</span><small>{evidence.source_title} · {evidence.snapshot_sha256.slice(0, 16)}…</small></li>)}</ul> : <Alert tone="info">No hay evidencia vinculada. La regla no puede publicarse como VERIFIED.</Alert>}</div></div> : <EmptyState title="No hay requisitos en esta revisión" description="El inspector permanece explícito cuando la fuente no contiene reglas estructuradas." />}</section>

            <section className="panel governance-section" aria-labelledby="governance-validation-title"><div className="section-heading"><div><p className="eyebrow">Validation report</p><h2 id="governance-validation-title">Bloqueos antes de publicar</h2></div></div>{proposal.validation_report.errors.length ? <ul className="governance-warning-list">{proposal.validation_report.errors.slice(0, 30).map((error) => <li key={error}>{error}</li>)}</ul> : <Alert tone="success">Sin errores estructurales detectados.</Alert>}{proposal.validation_report.warnings.length ? <ul className="governance-warning-list governance-warning-list-muted">{proposal.validation_report.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}</section>

            <section className="panel governance-section" aria-labelledby="governance-audit-title"><div className="section-heading"><div><p className="eyebrow">Audit trail</p><h2 id="governance-audit-title">Quién hizo qué y cuándo</h2></div></div>{auditEvents.length ? <ol className="governance-audit-list">{auditEvents.map((event) => <li key={event.id}><span>{event.created_at}</span><strong>{event.action}</strong><small>{event.actor ?? "sistema"} · {event.object_type}/{event.object_id}</small></li>)}</ol> : <p className="muted-copy">Aún no hay eventos para esta propuesta.</p>}</section>
          </>}
        </section>
      </div>
    </div>
  );
}
