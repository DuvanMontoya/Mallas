"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  applyGovernanceCandidates,
  getAssignmentPolicies,
  getGovernanceProposal,
  linkGovernanceRequirementEvidence,
  previewGovernanceCandidates,
  publishAssignmentPolicy,
  publishGovernanceProposal,
  problemMessage,
  reviewGovernanceCandidate,
  reviewGovernanceProposal,
  submitGovernanceProposal,
  submitAssignmentPolicy,
  type ApiFailure,
  type AssignmentPolicySummary,
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

function editorialStatus(status: string) {
  return ({ DRAFT: "Borrador", IN_REVIEW: "En revisión", APPROVED: "Aprobada", PUBLISHED: "Publicada", ACCEPTED: "Aceptado", REJECTED: "Rechazado", PENDING: "Pendiente", VERIFIED: "Verificado", UNKNOWN: "Por verificar", DISPUTED: "En disputa", INFERRED_PENDING_REVIEW: "Inferencia por revisar" } as Record<string, string>)[status] ?? status.replaceAll("_", " ").toLocaleLowerCase("es-CO");
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
      <td><StatusBadge tone={statusTone(candidate.status)} label={editorialStatus(candidate.status)} /></td>
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

function AssignmentPolicyReviewMaterial({ policy }: { policy: AssignmentPolicySummary }) {
  if (policy.status !== "IN_REVIEW") return null;
  return (
    <details>
      <summary>Ver material sometido</summary>
      <dl>
        <dt>Rango de admisión</dt><dd>{policy.admission_from ?? "Sin inicio"} – {policy.admission_to ?? "abierto"}</dd>
        <dt>Cohorte</dt><dd>{policy.cohort_code || "No restringida"}</dd>
        <dt>Plan anterior</dt><dd>{policy.previous_plan_code ?? "No aplica"}</dd>
        <dt>Publicación normativa</dt><dd>{policy.normative_published_on ?? "No demostrada"}</dd>
        <dt>Vigencia</dt><dd>{policy.effective_from ?? "Sin inicio"} – {policy.effective_to ?? "abierta"}</dd>
        <dt>Revisión objetivo</dt><dd>{policy.revision_code} · {policy.revision_status}</dd>
        <dt>Huella de contenido de revisión</dt><dd><code>{policy.revision_content_hash}</code></dd>
        <dt>Huella de fuentes de revisión</dt><dd><code>{policy.revision_source_set_hash}</code></dd>
        <dt>Permite revisión retirada</dt><dd>{policy.allow_retired_revision ? "Sí, explícitamente" : "No"}</dd>
        <dt>Huella del paquete</dt><dd><code>{policy.review_content_hash}</code></dd>
        <dt>Huella de evidencia de política</dt><dd><code>{policy.source_set_hash}</code></dd>
      </dl>
      {policy.evidence.map((item) => (
        <article key={`${item.purpose}-${item.excerpt_hash}`}>
          <strong>{item.purpose} · {item.source_title}</strong>
          <span>{item.locator}</span>
          <p>{item.excerpt}</p>
          <code>{item.excerpt_hash}</code>
          <code>{item.snapshot_sha256}</code>
        </article>
      ))}
    </details>
  );
}

function AssignmentPolicyGovernance({ roles, currentUserId }: { roles: string[]; currentUserId: number }) {
  const [policies, setPolicies] = useState<AssignmentPolicySummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");

  async function load() {
    const result = await getAssignmentPolicies();
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "No fue posible cargar las políticas de asignación.");
      return;
    }
    setPolicies(result.data);
    setLoaded(true);
  }

  async function publish(policy: AssignmentPolicySummary) {
    if (!window.confirm(`¿Publicar la política ${policy.policy_code}? Confirma que revisaste el paquete sellado y que no eres la persona preparadora.`)) return;
    setBusyId(policy.id);
    setError(null);
    const result = await publishAssignmentPolicy(policy.id);
    setBusyId(null);
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "La política no superó el gate de publicación.");
      return;
    }
    setPolicies((current) => current.map((item) => item.id === policy.id ? {
      ...item,
      status: result.data!.status,
      approved_by_id: result.data!.approved_by_id,
    } : item));
    setAnnouncement(`Política ${policy.policy_code} publicada por una segunda persona.`);
  }

  async function submit(policy: AssignmentPolicySummary) {
    setBusyId(policy.id);
    setError(null);
    const result = await submitAssignmentPolicy(policy.id);
    setBusyId(null);
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "La política no pudo enviarse a revisión.");
      return;
    }
    setPolicies((current) => current.map((item) => item.id === policy.id ? result.data! : item));
    setAnnouncement(`Política ${policy.policy_code} enviada a revisión. Otra persona debe publicarla.`);
  }

  return (
    <details className="governance-workflow panel" onToggle={(event) => {
      if (event.currentTarget.open && !loaded) void load();
    }}>
      <summary><span><b>Políticas de asignación curricular</b><small>Publicación evidenciada que decide plan y revisión</small></span></summary>
      <section aria-labelledby="assignment-policy-governance-title">
        <h2 id="assignment-policy-governance-title">Asignación automática</h2>
        <p className="muted-copy">Quien prepara la política la envía a revisión; una persona distinta debe publicarla. El servidor vuelve a comprobar evidencia, revisión, alcance, solapamientos y hashes.</p>
        <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
        {error ? <Alert tone="error">{error}</Alert> : null}
        {!loaded ? <p role="status">Cargando políticas…</p> : policies.length ? <div className="table-scroll"><table className="governance-table"><caption>Políticas dentro de su alcance editorial</caption><thead><tr><th>Política</th><th>Destino</th><th>Contexto</th><th>Estado</th><th><span className="sr-only">Acción</span></th></tr></thead><tbody>{policies.map((policy) => { const canSubmit = policy.status === "DRAFT" && roles.some((role) => ["EDITOR", "ADMIN"].includes(role)) && (policy.prepared_by_id === null || policy.prepared_by_id === currentUserId); const canPublish = policy.status === "IN_REVIEW" && roles.some((role) => ["REVIEWER", "ADMIN"].includes(role)) && policy.prepared_by_id !== currentUserId; return <tr key={policy.id}><td><strong>{policy.policy_code}</strong><small> v{policy.version} · {policy.program_name}</small><AssignmentPolicyReviewMaterial policy={policy} /></td><td>Plan {policy.plan_code} · {policy.revision_code}</td><td>{policy.context}</td><td><StatusBadge tone={statusTone(policy.status)} label={`${editorialStatus(policy.status)} · ${editorialStatus(policy.epistemic_status)}`} /></td><td>{canSubmit ? <button className="button button-primary" type="button" disabled={busyId === policy.id} onClick={() => void submit(policy)}>{busyId === policy.id ? `Enviando ${policy.policy_code}…` : `Enviar ${policy.policy_code} a revisión`}</button> : canPublish ? <button className="button button-primary" type="button" disabled={busyId === policy.id} onClick={() => void publish(policy)}>{busyId === policy.id ? `Publicando ${policy.policy_code}…` : `Publicar política verificada ${policy.policy_code}`}</button> : <span className="muted-copy">{policy.status === "IN_REVIEW" && policy.prepared_by_id === currentUserId ? "Esperando publicación por otra persona" : "Sin acción permitida para tu rol"}</span>}</td></tr>; })}</tbody></table></div> : <EmptyState title="Sin políticas preparadas" description="Las políticas aparecerán aquí después de su preparación y revisión evidenciada." />}
      </section>
    </details>
  );
}

export function GovernanceBackoffice({
  initialInbox,
  initialFailure,
  initialProposal,
  initialProposalEtag,
  initialProposalFailure,
  roles,
  currentUserId,
}: {
  initialInbox: SourceInbox | null;
  initialFailure: ApiFailure | null;
  initialProposal: GovernanceProposal | null;
  initialProposalEtag: string | null;
  initialProposalFailure: ApiFailure | null;
  roles: string[];
  currentUserId: number;
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
      <section className="governance-decision-hero">
        <div>
          <p className="eyebrow accent">Bandeja editorial</p>
          <h1>Revisiones curriculares</h1>
          <span>{inbox.proposals.length} propuestas · {inbox.documents.length} fuentes</span>
        </div>
        <div className="governance-hero-facts" aria-label="Resumen de la bandeja">
          <span><strong>{inbox.documents.length}</strong> documentos</span>
          <span><strong>{inbox.snapshots.length}</strong> snapshots</span>
          <span><strong>{inbox.proposals.length}</strong> propuestas</span>
        </div>
      </section>

      {failure ? <Alert tone={failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? "error" : "info"}><strong>{failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? "Conflicto de concurrencia." : "Estado editorial."}</strong> {failureText(failure)} {failure.problem?.code === "GOVERNANCE_CONCURRENCY_CONFLICT" ? <button className="button button-quiet" type="button" onClick={() => selectedId && void loadProposal(selectedId)}>Recargar versión actual</button> : null}</Alert> : null}

      <details className="governance-workflow panel"><summary><span><b>Cómo se protege una publicación</b><small>La cadena completa de procedencia y separación de funciones</small></span></summary><section aria-labelledby="governance-workflow-title"><h2 id="governance-workflow-title" className="sr-only">Flujo editorial completo</h2><ol className="governance-workflow-list">{inbox.workflow.map((stage, index) => <li key={stage}><span>{String(index + 1).padStart(2, "0")}</span><strong>{editorialStatus(stage)}</strong></li>)}</ol></section></details>

      <AssignmentPolicyGovernance roles={roles} currentUserId={currentUserId} />

      <div className="governance-layout">
        <aside className="panel governance-sidebar" aria-labelledby="governance-queue-title">
          <div className="section-heading"><div><p className="eyebrow">Cola de revisión</p><h2 id="governance-queue-title">Propuestas</h2></div><span className="tag tag-outline">{inbox.proposals.length}</span></div>
          <ul className="governance-proposal-list">
            {inbox.proposals.map((item: ProposalSummary) => <li key={item.id}><button className={selectedId === item.id ? "governance-proposal-card selected" : "governance-proposal-card"} type="button" onClick={() => { setSelectedId(item.id); void loadProposal(item.id); }}><span className="governance-card-top"><code>{item.candidate_revision_code}</code><StatusBadge tone={statusTone(item.status)} label={editorialStatus(item.status)} /></span><strong>{item.title}</strong><small>{item.pending_candidates} afirmaciones pendientes · {item.semantic_has_changes ? "cambia la revisión" : "sin cambios curriculares"}</small></button></li>)}
          </ul>
          <div className="governance-source-list"><h3>Snapshots recientes</h3>{inbox.snapshots.slice(0, 5).map((snapshot) => <article key={snapshot.id}><code>{snapshot.sha256.slice(0, 12)}…</code><p>{snapshot.document_title}</p><small>{snapshot.evidence_count} evidencias · {snapshot.mime_type}</small></article>)}</div>
        </aside>

        <section className="governance-main" aria-label="Detalle de la propuesta">
          {!proposal || busy ? <section className="panel governance-loading"><p className="eyebrow">Propuesta</p><h2>{busy ? "Cargando estado auditable…" : "Selecciona una propuesta"}</h2></section> : <>
            <section className="panel governance-detail-header">
              <div><p className="eyebrow accent">Revisión en borrador · {proposal.candidate_revision.plan_code}</p><h2>{proposal.title}</h2><p>{proposal.rationale}</p></div>
              <div className="governance-detail-meta"><StatusBadge tone={statusTone(proposal.status)} label={editorialStatus(proposal.status)} /><span>Versión <code>{proposal.version}</code></span><details><summary>Identificador técnico</summary><code>{proposal.content_fingerprint.slice(0, 16)}…</code></details></div>
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
              <article className="panel governance-metric"><span>Validación</span><strong>{proposal.validation_report.ok ? "Lista" : "Bloqueada"}</strong><small>{proposal.validation_report.errors.length} errores · {proposal.validation_report.unknowns.length} datos por verificar</small></article>
              <article className="panel governance-metric"><span>Diff semántico</span><strong>{diffCount(proposal).changed + diffCount(proposal).added + diffCount(proposal).removed}</strong><small>{diffCount(proposal).added} añadidos · {diffCount(proposal).removed} retirados · {diffCount(proposal).changed} cambios</small></article>
              <article className="panel governance-metric"><span>Impacto</span><strong>{proposal.impact_analysis.students_potentially_affected}</strong><small>estudiantes potencialmente afectados · {proposal.impact_analysis.audits_affected} auditorías</small></article>
            </section>

            {publicationEvent(proposal) ? <section className="panel governance-section governance-publication-impact" aria-labelledby="governance-publication-impact-title"><div className="section-heading"><div><p className="eyebrow">Evento de publicación</p><h2 id="governance-publication-impact-title">Impacto materializado después de publicar</h2><p>La revisión anterior conserva sus auditorías; cada matrícula afectada tiene un plan de recomputación que requiere decisión de cohorte.</p></div><StatusBadge tone="passed" label="INMUTABLE" /></div><div className="governance-impact-summary">{(() => { const event = publicationEvent(proposal); if (!event) return null; return <><article><strong>{event.impact_summary.affected_enrollments}</strong><span>matrículas identificadas</span></article><article><strong>{event.impact_summary.affected_audits}</strong><span>auditorías preservadas</span></article><article><strong>{event.impact_summary.changed_courses + event.impact_summary.changed_groups + event.impact_summary.changed_requirements}</strong><span>familias semánticas afectadas</span></article><article><strong>{event.notification_plan.recipient_count}</strong><span>notificaciones encoladas tras commit</span></article></>; })()}</div><div className="governance-impact-list"><h3>Plan de recomputación</h3>{(() => { const event = publicationEvent(proposal); if (!event) return null; return event.enrollment_impacts.length ? <ul>{event.enrollment_impacts.slice(0, 20).map((impact) => <li key={impact.id}><strong>{impact.impact_status}</strong><code>{impact.recompute_job_key}</code><small>{impact.previous_audit_run_id ? `Auditoría anterior ${impact.previous_audit_result_hash.slice(0, 16)}…` : "Sin auditoría previa persistida"} · decisión de revisión requerida</small></li>)}</ul> : <p className="muted-copy">No hay matrículas con la revisión anterior; el plan de recomputación no requiere trabajos.</p>; })()}</div></section> : null}

            <section className="panel governance-section" aria-labelledby="governance-diff-title"><div className="section-heading"><div><p className="eyebrow">Diferencia semántica</p><h2 id="governance-diff-title">Cambios que el revisor debe entender</h2></div></div><div className="governance-diff-grid">{Object.entries(currentDiff?.added ?? {}).map(([entity, rows]) => <div key={`add-${entity}`} className="governance-diff-card governance-diff-added"><strong>{entity} añadidos</strong><span>{Array.isArray(rows) ? rows.length : 0}</span></div>)}{Object.entries(currentDiff?.removed ?? {}).map(([entity, rows]) => <div key={`remove-${entity}`} className="governance-diff-card governance-diff-removed"><strong>{entity} retirados</strong><span>{Array.isArray(rows) ? rows.length : 0}</span></div>)}{(currentDiff?.changed ?? []).slice(0, 12).map((item, index) => <details className="governance-diff-change" key={`${item.entity}-${item.key}-${index}`}><summary><strong>{item.entity}</strong> · {item.key}</summary><div><pre>{JSON.stringify({ before: item.before, after: item.after }, null, 2)}</pre></div></details>)}</div></section>

            <section className="panel governance-section" aria-labelledby="governance-candidates-title"><div className="section-heading"><div><p className="eyebrow">Candidatos de extracción</p><h2 id="governance-candidates-title">Revisión de afirmaciones extraídas</h2><p>La selección masiva siempre requiere una previsualización sin escrituras antes de aplicar.</p></div><div className="governance-row-actions"><button className="button button-secondary" type="button" disabled={!selectedCandidates.length || busy} onClick={() => void previewBulk()}>Previsualizar aceptación masiva</button>{bulkPreview ? <button className="button button-primary" type="button" disabled={busy || bulkPreview.blocked > 0} onClick={() => void applyBulk()}>Aplicar preview ({bulkPreview.allowed})</button> : null}</div></div>{bulkPreview ? <Alert tone={bulkPreview.blocked ? "error" : "success"}><strong>Preview sin escrituras:</strong> {bulkPreview.total} seleccionados, {bulkPreview.allowed} aplicables, {bulkPreview.blocked} bloqueados.</Alert> : null}<div className="table-scroll"><table className="governance-table"><caption>Candidatos extraídos de {proposal.source_snapshot.sha256.slice(0, 16)}…</caption><thead><tr><th scope="col">Seleccionar</th><th scope="col">Entidad</th><th scope="col">Operación</th><th scope="col">Estado</th><th scope="col">Evidencia</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead><tbody>{proposal.candidates.slice(0, 80).map((candidate) => <CandidateRow key={candidate.id} candidate={candidate} selected={selectedCandidates.includes(candidate.id)} onToggle={() => setSelectedCandidates((current) => current.includes(candidate.id) ? current.filter((id) => id !== candidate.id) : [...current, candidate.id])} onReview={(item, status) => void reviewCandidate(item, status)} busy={busy} />)}</tbody></table></div></section>

            <details className="governance-technical panel"><summary><span><b>Inspeccionar reglas y evidencia</b><small>Explicación humana, estructura determinista y procedencia</small></span></summary><section className="governance-section" aria-labelledby="governance-rule-title"><div className="section-heading"><div><p className="eyebrow">Inspector de reglas</p><h2 id="governance-rule-title">Qué significa la regla y de dónde sale</h2></div><label className="field-group"><span>Regla</span><select value={selectedRequirement?.id ?? ""} onChange={(event) => setSelectedRequirementId(event.target.value)}>{proposal.requirements.slice(0, 80).map((requirement) => <option key={requirement.id} value={requirement.id}>{requirement.code} · {editorialStatus(requirement.epistemic_status)}</option>)}</select></label></div>{selectedRequirement ? <div className="governance-rule-grid"><div className="governance-rule-copy"><StatusBadge tone={statusTone(selectedRequirement.epistemic_status)} label={editorialStatus(selectedRequirement.epistemic_status)} /><h3>{selectedRequirement.code}</h3><p>{selectedRequirement.human_explanation}</p><p className="muted-copy">{selectedRequirement.purpose}</p><button className="button button-secondary" type="button" disabled={busy || !selectedRequirement.evidence.length} onClick={() => void linkSelectedRequirementEvidence()}>Guardar vínculos de evidencia</button></div><details><summary>Ver estructura determinista</summary><pre className="governance-ast">{JSON.stringify(selectedRequirement.ast, null, 2)}</pre></details><div><h3>Evidencia vinculada</h3>{selectedRequirement.evidence.length ? <ul className="governance-evidence-list">{selectedRequirement.evidence.map((evidence) => <li key={evidence.id}><strong>{evidence.locator}</strong><span>{evidence.excerpt}</span><small>{evidence.source_title}</small></li>)}</ul> : <Alert tone="info">No hay evidencia vinculada. La regla no puede publicarse como verificada.</Alert>}</div></div> : <EmptyState title="No hay requisitos en esta revisión" description="No se encontraron reglas estructuradas para inspeccionar." />}</section></details>

            <section className="panel governance-section" aria-labelledby="governance-validation-title"><div className="section-heading"><div><p className="eyebrow">Informe de validación</p><h2 id="governance-validation-title">Bloqueos antes de publicar</h2></div></div>{proposal.validation_report.errors.length ? <ul className="governance-warning-list">{proposal.validation_report.errors.slice(0, 30).map((error) => <li key={error}>{error}</li>)}</ul> : <Alert tone="success">Sin errores estructurales detectados.</Alert>}{proposal.validation_report.warnings.length ? <ul className="governance-warning-list governance-warning-list-muted">{proposal.validation_report.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}</section>

            <section className="panel governance-section" aria-labelledby="governance-audit-title"><div className="section-heading"><div><p className="eyebrow">Trazabilidad de auditoría</p><h2 id="governance-audit-title">Quién hizo qué y cuándo</h2></div></div>{auditEvents.length ? <ol className="governance-audit-list">{auditEvents.map((event) => <li key={event.id}><span>{event.created_at}</span><strong>{event.action}</strong><small>{event.actor ?? "sistema"} · {event.object_type}/{event.object_id}</small></li>)}</ol> : <p className="muted-copy">Aún no hay eventos para esta propuesta.</p>}</section>
          </>}
        </section>
      </div>
    </div>
  );
}
