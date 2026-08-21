"use client";
/* eslint-disable react-hooks/set-state-in-effect, react-hooks/preserve-manual-memoization -- wizard and catalog sync require derived state initialization that is intentionally synchronized via effects and manual memoization is intentional for catalog filtering */

import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import {
  approveAdminOverrideAuthorization,
  confirmAdminEnrollmentRevision,
  createAcademicTerm,
  createAdminEnrollment,
  createAdminEnrollmentTransition,
  createAdminOverrideAuthorization,
  getAdminEnrollmentIdentity,
  getAdminEnrollments,
  getAdminOverrideAuthorizations,
  getAdminOverrideEvidence,
  getStudentAdminCatalog,
  overrideAdminEnrollmentAssignment,
  previewAdminCurriculumAssignment,
  previewAdminEnrollmentTransition,
  updateAdminEnrollmentIdentity,
  verifyAdminAdmissionFact,
  type AdminEnrollment,
  type AdminEnrollmentSummary,
  type AdminEnrollmentCreatePayload,
  type AdminEnrollmentPage,
  type AdminAssignmentPreview,
  type AdminOverrideAuthorization,
  type AdminOverrideEvidence,
  type StudentAdminCatalog,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

function firstId<T extends { id: string }>(items: T[]) {
  return items[0]?.id ?? "";
}

function assignmentReason(code: string) {
  return (
    ({
      EXACT_VERIFIED_POLICY: "Existe una única política publicada y verificada",
      NO_APPLICABLE_POLICY: "No existe una política aplicable",
      MULTIPLE_APPLICABLE_POLICIES: "Varias políticas compiten por estos datos",
      EVIDENCE_INSUFFICIENT: "La evidencia institucional es insuficiente",
      ADMISSION_FACT_REQUIRED: "Falta verificar el hecho individual de admisión",
    } as Record<string, string>)[code] ??
    `Motivo institucional: ${code.replaceAll("_", " ").toLocaleLowerCase("es-CO")}`
  );
}

function friendlyAdmissionError(detail?: string | null) {
  if (!detail) return "No encontramos un acta archivada para ese código en este programa y período. Verifica el código o déjalo vacío para crear en revisión.";
  if (detail.includes("Exactly one archived")) return "No encontramos un acta única para ese código en este programa y período. Debe haber exactamente un documento archivado que coincida con el código, programa y período. Verifica el código tal como aparece en Fuentes, o deja el campo vacío para crear la matrícula en revisión pendiente.";
  if (detail.includes("admission manifest") || detail.includes("admission fact")) return "El soporte no coincide con el programa o período seleccionado o no está archivado como manifiesto de admisión. Revisa que el acta esté cargada en Fuentes.";
  return detail;
}

function initialsFrom(displayName: string, email: string) {
  const source = displayName.trim() || email.trim();
  if (!source) return "?";
  const parts = source.split(/\s+/).filter(Boolean).slice(0, 2);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function toEnrollmentSummary(value: AdminEnrollment): AdminEnrollmentSummary {
  return {
    id: value.id,
    student_profile_id: value.student_profile_id,
    email: value.email,
    display_name: value.display_name,
    identity_data_status: value.identity_data_status,
    student_number: value.student_number,
    institution_id: value.institution_id,
    program_id: value.program_id,
    program_name: value.program_name,
    plan_id: value.plan_id,
    plan_code: value.plan_code,
    revision_basis_id: value.revision_basis_id,
    admission_term_id: value.admission_term_id,
    admission_term_code: value.admission_term_code,
    status: value.status,
    cohort_code: value.cohort_code,
    review_reasons: value.review_reasons,
    version: value.version,
  };
}

function AssignmentPreviewCard({
  assignment,
  loading,
}: {
  assignment: AdminAssignmentPreview | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="assignment-preview assignment-preview--loading" role="status" aria-live="polite">
        <span className="skeleton skeleton-line" style={{ width: "60%" }} />
        <span className="skeleton skeleton-line" style={{ width: "85%" }} />
        <span className="skeleton skeleton-line" style={{ width: "40%" }} />
        <span>Comprobando política curricular…</span>
      </div>
    );
  }
  if (!assignment) {
    return (
      <div className="assignment-preview assignment-preview--empty">
        <p className="muted-copy">Selecciona programa y período para evaluar la asignación.</p>
      </div>
    );
  }
  const isResolved = assignment.status === "RESOLVED";
  const tone = isResolved ? "success" : "warning";
  return (
    <div className={`assignment-preview assignment-preview--${tone}`}>
      <div className="assignment-preview__header">
        <span className={`assignment-preview__icon assignment-preview__icon--${tone}`} aria-hidden="true">
          {isResolved ? "✓" : "!"}
        </span>
        <div>
          <strong>
            {isResolved
              ? `Asignación automática: plan ${assignment.selected_plan_code} · revisión ${assignment.selected_revision_code}`
              : "Sin asignación automática — quedará en revisión"}
          </strong>
          <small>
            {assignment.reason_codes.map(assignmentReason).join(" · ") || "Sin razón adicional"} · {assignment.admission_term_code}
          </small>
        </div>
      </div>
      <dl className="assignment-preview__facts">
        <div>
          <dt>Hecho de admisión</dt>
          <dd>
            <StatusBadge tone={assignment.admission_fact_status === "VERIFIED" ? "passed" : "unknown"} label={assignment.admission_fact_status === "VERIFIED" ? "Verificado" : "Pendiente"} />
          </dd>
        </div>
        <div>
          <dt>Fuente del período</dt>
          <dd>
            <StatusBadge tone={assignment.admission_term_source_status === "VERIFIED" ? "passed" : "unknown"} label={assignment.admission_term_source_status === "VERIFIED" ? "Verificada" : "No verificada"} />
          </dd>
        </div>
        <div>
          <dt>Motor</dt>
          <dd>
            <code>{assignment.resolver_version}</code>
          </dd>
        </div>
        <div>
          <dt>Huella</dt>
          <dd>
            <code title={assignment.decision_hash}>{assignment.decision_hash.slice(0, 16)}…</code>
          </dd>
        </div>
      </dl>
      <details className="assignment-preview__trace">
        <summary>Ver trazabilidad técnica</summary>
        <p>
          Decisión <code>{assignment.decision_hash}</code>
        </p>
        {assignment.candidates.length ? (
          <ul className="assignment-preview__candidates">
            {assignment.candidates.map((c) => (
              <li key={c.policy_id}>
                <strong>{c.policy_code}</strong> · {c.epistemic_status} · {c.revision_status} · {c.evidence_ids.length} evidencias · <code>{c.content_hash.slice(0, 12)}…</code>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted-copy">No hubo políticas candidatas para estos datos.</p>
        )}
      </details>
    </div>
  );
}

function EnrollmentResolution({
  enrollment,
  catalog,
  currentUserId,
  onResolved,
}: {
  enrollment: AdminEnrollmentSummary;
  catalog: StudentAdminCatalog;
  currentUserId: number;
  onResolved: (value: AdminEnrollmentSummary) => void;
}) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [authorizations, setAuthorizations] = useState<AdminOverrideAuthorization[]>([]);
  const [evidence, setEvidence] = useState<AdminOverrideEvidence[]>([]);
  const [governanceLoaded, setGovernanceLoaded] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const label = enrollment.display_name || enrollment.student_number || enrollment.email;
  const admissionTerm = catalog.terms.find((term) => term.id === enrollment.admission_term_id);
  const plans = catalog.plans.filter((plan) => plan.program_id === enrollment.program_id);
  const [overridePlanId, setOverridePlanId] = useState(plans[0]?.id ?? "");
  const revisions = catalog.revisions.filter((revision) => revision.plan_id === overridePlanId);

  async function loadGovernance() {
    setError(null);
    const [authorizationResult, evidenceResult] = await Promise.all([
      getAdminOverrideAuthorizations(enrollment.id),
      getAdminOverrideEvidence(enrollment.id),
    ]);
    if (!authorizationResult.data || !evidenceResult.data) {
      setError(authorizationResult.failure?.problem?.detail ?? evidenceResult.failure?.problem?.detail ?? "No fue posible cargar el expediente de gobernanza.");
      return;
    }
    setAuthorizations(authorizationResult.data);
    setEvidence(evidenceResult.data);
    setGovernanceLoaded(true);
  }

  return (
    <details
      className="enrollment-action"
      onToggle={(event) => {
        if (event.currentTarget.open && !governanceLoaded) void loadGovernance();
      }}
    >
      <summary>Reevaluar asignación curricular de {label}</summary>
      <div className="enrollment-action__body">
        <p className="muted-copy">
          <strong>Ingreso {enrollment.admission_term_code}</strong>
          {admissionTerm ? ` · ${admissionTerm.starts_at.slice(0, 10)}` : ""} — El sistema reevalúa exclusivamente políticas publicadas y verificadas. No se elige plan manualmente.
        </p>
        {error ? <Alert tone="error">{error}</Alert> : null}
        <button
          className="button button-primary"
          type="button"
          disabled={pending}
          onClick={() =>
            startTransition(async () => {
              setError(null);
              const result = await confirmAdminEnrollmentRevision(enrollment.id, {}, enrollment.version);
              if (!result.data) {
                setError(result.failure?.problem?.detail ?? "Todavía no existe una política verificable para activar esta matrícula.");
                return;
              }
              setAnnouncement(`Asignación curricular actualizada para ${label}.`);
              onResolved(result.data);
            })
          }
        >
          {pending ? `Reevaluando política de ${label}…` : `Reevaluar política de ${label}`}
        </button>
      </div>
      <form
        className="governed-override-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          startTransition(async () => {
            setError(null);
            const result = await createAdminOverrideAuthorization(enrollment.id, {
              plan_id: String(form.get("override_plan_id") ?? ""),
              revision_basis_id: String(form.get("override_revision_id") ?? ""),
              evidence_id: String(form.get("override_evidence_id") ?? ""),
              reason_code: String(form.get("override_reason_code") ?? ""),
            });
            if (!result.data) {
              setError(result.failure?.problem?.detail ?? "No fue posible preparar la autorización.");
              return;
            }
            setAuthorizations((current) => [result.data!, ...current]);
          });
        }}
      >
        <fieldset>
          <legend>Preparar excepción institucional para {label}</legend>
          <p className="muted-copy">Una persona prepara y otra aprueba. Al aprobar, evidencia y revisión quedan selladas con hash inmutable.</p>
          <label className="field-group">
            <span>Plan propuesto</span>
            <select name="override_plan_id" required value={overridePlanId} onChange={(event) => setOverridePlanId(event.target.value)}>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.code} · {plan.title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-group">
            <span>Revisión autorizada</span>
            <select name="override_revision_id" required>
              {revisions.map((revision) => (
                <option key={revision.id} value={revision.id}>
                  {revision.code} · {revision.status}
                </option>
              ))}
            </select>
          </label>
          <label className="field-group">
            <span>Motivo aprobado</span>
            <select name="override_reason_code" required>
              <option value="ADMISSION_POLICY_EXCEPTION">Excepción a política de admisión</option>
              <option value="REENTRY_INSTITUTIONAL_DECISION">Decisión institucional de reingreso</option>
              <option value="TRANSITION_INSTITUTIONAL_DECISION">Decisión institucional de transición</option>
              <option value="LEGACY_RECORD_VERIFIED">Registro histórico verificado</option>
            </select>
          </label>
          <label className="field-group">
            <span>Evidencia archivada</span>
            <select name="override_evidence_id" required disabled={!governanceLoaded || evidence.length === 0}>
              {evidence.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.source_title} · {item.locator} · {item.excerpt.slice(0, 90)}
                </option>
              ))}
            </select>
          </label>
          {!governanceLoaded ? (
            <p role="status">Cargando expediente de gobernanza…</p>
          ) : evidence.length === 0 ? (
            <Alert tone="warning">No hay evidencia archivada disponible. La excepción no puede prepararse.</Alert>
          ) : null}
          <button className="button button-secondary" type="submit" disabled={pending || evidence.length === 0}>
            {pending ? `Preparando excepción de ${label}…` : `Enviar excepción de ${label} para aprobación`}
          </button>
        </fieldset>
      </form>
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
      <section aria-label={`Autorizaciones para ${enrollment.display_name || enrollment.student_number}`} className="authorizations-list">
        <h3>Autorizaciones</h3>
        {authorizations.length === 0 && governanceLoaded ? (
          <p className="empty-copy">No hay solicitudes preparadas.</p>
        ) : (
          authorizations.map((authorization) => (
            <article key={authorization.id} className="authorization-card">
              <div>
                <strong>
                  Plan {authorization.plan_code} · revisión {authorization.revision_code} ({authorization.revision_status})
                </strong>
                <span>
                  {authorization.reason_code} · {authorization.status === "APPROVED" ? "Aprobada y sellada" : "Pendiente de segunda aprobación"}
                </span>
                <dl>
                  <dt>Versión del sello</dt>
                  <dd>{authorization.seal_version}</dd>
                  <dt>Fuente congelada</dt>
                  <dd>{authorization.evidence_source_title}</dd>
                  <dt>Localizador</dt>
                  <dd>{authorization.evidence_locator}</dd>
                  <dt>Extracto revisado</dt>
                  <dd>{authorization.evidence_excerpt}</dd>
                  <dt>Huella del extracto</dt>
                  <dd>
                    <code>{authorization.evidence_excerpt_hash}</code>
                  </dd>
                </dl>
              </div>
              {authorization.status === "DRAFT" ? (
                authorization.prepared_by_id === currentUserId ? (
                  <div>
                    <Alert tone="warning">Tú preparaste esta solicitud. Entrega el expediente a otra persona autorizada y actualiza la lista para continuar.</Alert>
                    <button className="button button-secondary" type="button" onClick={() => void loadGovernance()}>
                      {`Actualizar autorizaciones de ${label}`}
                    </button>
                  </div>
                ) : (
                  <button
                    className="button button-secondary"
                    type="button"
                    disabled={pending}
                    onClick={() =>
                      startTransition(async () => {
                        const result = await approveAdminOverrideAuthorization(authorization.id, authorization.version);
                        if (!result.data) {
                          setError(result.failure?.problem?.detail ?? "Otra persona autorizada debe aprobar la solicitud.");
                          return;
                        }
                        setAuthorizations((current) => current.map((item) => (item.id === result.data!.id ? result.data! : item)));
                        setAnnouncement(`Excepción de ${label} aprobada y sellada por una segunda persona.`);
                      })
                    }
                  >
                    {`Aprobar excepción de ${label} como segunda persona`}
                  </button>
                )
              ) : (
                <button
                  className="button button-primary"
                  type="button"
                  disabled={pending}
                  onClick={() =>
                    startTransition(async () => {
                      const result = await overrideAdminEnrollmentAssignment(enrollment.id, { authorization_id: authorization.id }, enrollment.version);
                      if (!result.data) {
                        setError(result.failure?.problem?.detail ?? "No fue posible aplicar la autorización sellada.");
                        return;
                      }
                      setAnnouncement(`Autorización sellada aplicada a ${label}.`);
                      onResolved(result.data);
                    })
                  }
                >
                  {`Aplicar autorización sellada a ${label}`}
                </button>
              )}
            </article>
          ))
        )}
      </section>
    </details>
  );
}

function EnrollmentTransition({
  enrollment,
  catalog,
  onCreated,
}: {
  enrollment: AdminEnrollmentSummary;
  catalog: StudentAdminCatalog;
  onCreated: (value: AdminEnrollmentSummary) => void;
}) {
  const program = catalog.programs.find((item) => item.id === enrollment.program_id);
  const sourceTerm = catalog.terms.find((term) => term.id === enrollment.admission_term_id);
  const terms = catalog.terms.filter(
    (term) => term.institution_id === enrollment.institution_id && (!term.campus_id || term.campus_id === program?.campus_id) && (!sourceTerm || term.starts_at > sourceTerm.starts_at),
  );
  const reentryAllowed = ["COMPLETED", "SUSPENDED", "WITHDRAWN", "TRANSITIONED"].includes(enrollment.status);
  const [preview, setPreview] = useState<AdminAssignmentPreview | null>(null);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const label = enrollment.display_name || enrollment.student_number || enrollment.email;
  const [targetTermId, setTargetTermId] = useState(terms[0]?.id ?? "");
  const [reference, setReference] = useState("");
  const [admissionVerified, setAdmissionVerified] = useState(false);
  const [admissionVerifying, setAdmissionVerifying] = useState(false);
  const verificationSequence = useRef(0);

  function invalidateTransitionVerification() {
    verificationSequence.current += 1;
    setAdmissionVerified(false);
    setAdmissionVerifying(false);
    setPreview(null);
  }

  async function verifyTransitionAdmission() {
    if (!targetTermId || !reference.trim()) return;
    const sequence = ++verificationSequence.current;
    setAdmissionVerifying(true);
    setError(null);
    const result = await verifyAdminAdmissionFact({
      program_id: enrollment.program_id,
      admission_term_id: targetTermId,
      record_reference: reference.trim(),
      source_enrollment_id: enrollment.id,
    });
    if (sequence !== verificationSequence.current) return;
    setAdmissionVerifying(false);
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "El manifiesto no demuestra esta admisión individual.");
      return;
    }
    setAdmissionVerified(true);
  }

  return (
    <details className="enrollment-action">
      <summary>Registrar reingreso o transición de {enrollment.display_name || enrollment.student_number}</summary>
      <form
        className="transition-form"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const payload = {
            admission_term_id: targetTermId,
            context: String(form.get("transition_context") ?? "REENTRY"),
            cohort_code: String(form.get("transition_cohort") ?? ""),
            admission_verification_method: admissionVerified ? "VERIFIED_ADMISSION_FACT" : "SOURCE_SNAPSHOT",
            admission_record_reference: reference.trim() || null,
          };
          startTransition(async () => {
            setError(null);
            if (!preview) {
              const result = await previewAdminEnrollmentTransition(enrollment.id, payload);
              if (!result.data) {
                setError(result.failure?.problem?.detail ?? "No fue posible evaluar el reingreso o transición.");
                return;
              }
              setPreview(result.data);
              return;
            }
            const result = await createAdminEnrollmentTransition(enrollment.id, {
              ...payload,
              expected_assignment_hash: preview.decision_hash,
            });
            if (!result.data) {
              setError(result.failure?.problem?.detail ?? "No fue posible registrar la nueva matrícula.");
              return;
            }
            setPreview(null);
            onCreated(result.data);
          });
        }}
        onChange={() => setPreview(null)}
      >
        <fieldset>
          <legend>Nueva vinculación del mismo estudiante</legend>
          <p className="muted-copy">El plan anterior se deriva de esta matrícula; no se escribe manualmente. Una política publicada debe resolver el nuevo plan o la nueva matrícula quedará en revisión.</p>
          <label className="field-group">
            <span>Contexto</span>
            <select name="transition_context">{reentryAllowed ? <option value="REENTRY">Reingreso</option> : <option value="PLAN_TRANSITION">Transición de plan</option>}</select>
          </label>
          <label className="field-group">
            <span>Nuevo período</span>
            <select name="transition_term_id" required value={targetTermId} onChange={(event) => { setTargetTermId(event.target.value); invalidateTransitionVerification(); }}>
              {terms.map((term) => (
                <option key={term.id} value={term.id}>
                  {term.code} · fuente {term.admission_source_status === "VERIFIED" ? "verificada" : "pendiente"}
                </option>
              ))}
            </select>
          </label>
          <label className="field-group">
            <span>Cohorte (opcional)</span>
            <input name="transition_cohort" />
          </label>
          <label className="field-group">
            <span>Referencia institucional de la nueva admisión</span>
            <input name="transition_reference" value={reference} onChange={(event) => { setReference(event.target.value); invalidateTransitionVerification(); }} />
            <small>Es obligatoria para una asignación automática; debe corresponder a un manifiesto individual archivado para este estudiante, programa y período.</small>
          </label>
          <button className="button button-secondary" type="button" disabled={!targetTermId || !reference.trim() || admissionVerified || admissionVerifying} onClick={() => void verifyTransitionAdmission()}>
            {admissionVerified ? `Admisión de ${label} verificada y sellada` : admissionVerifying ? `Verificando admisión de ${label}…` : `Verificar admisión de ${label}`}
          </button>
          {preview ? (
            <>
              {preview.input.context === "PLAN_TRANSITION" ? (
                <Alert tone="warning">
                  <strong>Efecto sobre la matrícula origen:</strong> cambiará de {enrollment.status} a TRANSITIONED aunque el nuevo plan quede pendiente de revisión.
                </Alert>
              ) : (
                <Alert tone="info">La matrícula histórica de origen conservará su estado {enrollment.status}; se creará una vinculación separada de reingreso.</Alert>
              )}
              {preview.status === "RESOLVED" ? (
                <Alert tone="success">
                  <strong>Destino verificado para {label}:</strong> plan {preview.selected_plan_code}, revisión {preview.selected_revision_code}, período {preview.admission_term_code}.
                </Alert>
              ) : (
                <Alert tone="warning">La nueva matrícula quedará en revisión; no se seleccionó un plan automáticamente.</Alert>
              )}
              <AssignmentPreviewCard assignment={preview} loading={false} />
            </>
          ) : null}
          {error ? <Alert tone="error">{error}</Alert> : null}
          <button className="button button-secondary" type="submit" disabled={pending || terms.length === 0}>
            {pending ? `Procesando vinculación de ${label}…` : preview ? `Confirmar nueva matrícula de ${label}` : `Evaluar asignación de ${label}`}
          </button>
        </fieldset>
      </form>
    </details>
  );
}

function IdentityRectification({
  enrollment,
  onUpdated,
}: {
  enrollment: AdminEnrollmentSummary;
  onUpdated: (value: AdminEnrollmentSummary) => void;
}) {
  const [identity, setIdentity] = useState<AdminEnrollment | null>(null);
  const identityRequestSequence = useRef(0);
  const [loading, setLoading] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const label = enrollment.display_name || enrollment.student_number || enrollment.email;
  const legendId = `identity-legend-${enrollment.id}`;
  const errorId = `identity-error-${enrollment.id}`;

  async function loadIdentity() {
    if (identity || loading) return;
    const sequence = ++identityRequestSequence.current;
    setLoading(true);
    setError(null);
    const result = await getAdminEnrollmentIdentity(enrollment.id);
    if (sequence !== identityRequestSequence.current) return;
    setLoading(false);
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "No fue posible cargar la identidad privada.");
      return;
    }
    setIdentity(result.data);
  }

  return (
    <details
      className="enrollment-action"
      onToggle={(event) => {
        if (event.currentTarget.open) void loadIdentity();
        else {
          identityRequestSequence.current += 1;
          setIdentity(null);
          setLoading(false);
          setError(null);
        }
      }}
    >
      <summary>Revisar identidad de {label}</summary>
      {loading ? <p role="status">Cargando identidad privada…</p> : null}
      {identity ? (
        <form
          key={identity.identity_version}
          aria-labelledby={legendId}
          aria-describedby={error ? errorId : undefined}
          onSubmit={(event) => {
            event.preventDefault();
            setError(null);
            const form = new FormData(event.currentTarget);
            startTransition(async () => {
              const result = await updateAdminEnrollmentIdentity(
                enrollment.id,
                {
                  first_name: String(form.get("first_name") ?? ""),
                  middle_names: String(form.get("middle_names") ?? ""),
                  first_surname: String(form.get("first_surname") ?? ""),
                  second_surname: String(form.get("second_surname") ?? ""),
                  preferred_name: String(form.get("preferred_name") ?? ""),
                  birth_date: String(form.get("birth_date") ?? ""),
                  rationale: String(form.get("rationale") ?? "OTHER_VERIFIED"),
                },
                identity.identity_version,
              );
              if (!result.data) {
                setError(result.failure?.problem?.detail ?? "No fue posible rectificar la identidad.");
                return;
              }
              setIdentity(result.data);
              onUpdated(toEnrollmentSummary(result.data));
            });
          }}
        >
          <fieldset>
            <legend id={legendId}>Identidad de {label} · {enrollment.student_number}</legend>
            <p className="muted-copy">La rectificación queda auditada sin copiar nombres ni fecha de nacimiento al evento.</p>
            <label className="field-group">
              <span>Primer nombre de {label}</span>
              <input name="first_name" defaultValue={identity.first_name} required />
            </label>
            <label className="field-group">
              <span>Otros nombres de {label}</span>
              <input name="middle_names" defaultValue={identity.middle_names} />
            </label>
            <label className="field-group">
              <span>Primer apellido de {label}</span>
              <input name="first_surname" defaultValue={identity.first_surname} required />
            </label>
            <label className="field-group">
              <span>Segundo apellido de {label}</span>
              <input name="second_surname" defaultValue={identity.second_surname} />
            </label>
            <label className="field-group">
              <span>Nombre preferido de {label}</span>
              <input name="preferred_name" defaultValue={identity.preferred_name} />
            </label>
            <label className="field-group">
              <span>Fecha de nacimiento de {label}</span>
              <input name="birth_date" type="date" defaultValue={identity.birth_date ?? ""} required />
            </label>
            <label className="field-group">
              <span>Fundamento verificado</span>
              <select name="rationale" defaultValue="STUDENT_REQUEST_VERIFIED">
                <option value="STUDENT_REQUEST_VERIFIED">Solicitud de la persona verificada</option>
                <option value="AUTHORIZED_SOURCE_VERIFIED">Fuente institucional autorizada</option>
                <option value="DATA_ENTRY_CORRECTION">Corrección de digitación comprobada</option>
                <option value="OTHER_VERIFIED">Otro fundamento verificado</option>
              </select>
            </label>
            {error ? (
              <div id={errorId}>
                <Alert tone="error">{error}</Alert>
              </div>
            ) : null}
            <button className="button button-primary" type="submit" disabled={pending}>
              {pending ? `Guardando identidad de ${label}…` : `Guardar identidad de ${label}`}
            </button>
          </fieldset>
        </form>
      ) : null}
      {!loading && !identity && error ? (
        <div id={errorId}>
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}
    </details>
  );
}

export function StudentAdministrationWorkspace({
  catalog,
  initialPage,
  currentUserId,
}: {
  catalog: StudentAdminCatalog;
  initialPage: AdminEnrollmentPage;
  currentUserId: number;
}) {
  const [enrollments, setEnrollments] = useState(initialPage.items);
  const [total, setTotal] = useState(initialPage.total);
  const [page, setPage] = useState(initialPage);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "ACTIVE" | "NEEDS_REVIEW">("ALL");
  const [searching, setSearching] = useState(false);
  const initialSearchRender = useRef(true);
  const searchRequestSequence = useRef(0);

  // Wizard state — keep context fields at top level so preview + verification stay together
  const [liveCatalog, setLiveCatalog] = useState(catalog);
  useEffect(() => setLiveCatalog(catalog), [catalog]);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [institutionId, setInstitutionId] = useState(firstId(catalog.institutions));
  const programs = useMemo(() => liveCatalog.programs.filter((p) => p.institution_id === institutionId), [liveCatalog.programs, institutionId]);
  const [programId, setProgramId] = useState(firstId(programs));
  const activeProgram = programs.find((p) => p.id === programId) ?? programs[0];
  // Periods are institution-scoped. Campus filtering is only for governance display, not for creation UX.
  // Showing all institution terms prevents the empty-select bug reported in production.
  const terms = useMemo(
    () => {
      const byInstitution = liveCatalog.terms.filter((t) => t.institution_id === institutionId);
      // Prefer terms that match the program campus, but never hide all terms — fallback to institution list.
      if (!activeProgram?.campus_id) return byInstitution;
      const byCampus = byInstitution.filter((t) => !t.campus_id || t.campus_id === activeProgram.campus_id);
      return byCampus.length ? byCampus : byInstitution;
    },
    [liveCatalog.terms, institutionId, activeProgram?.campus_id],
  );
  const [termId, setTermId] = useState(firstId(terms));
  // Keep term selection in sync if liveCatalog refreshes and current term disappears
  useEffect(() => {
    if (terms.length && !terms.some((t) => t.id === termId)) setTermId(terms[0].id);
  }, [terms, termId]);
  // Inline period creator (visible when terms empty or via "Crear nuevo período")
  const [showTermCreator, setShowTermCreator] = useState(false);
  const [termCodeDraft, setTermCodeDraft] = useState("2026-1S");
  const [termStartsDraft, setTermStartsDraft] = useState("2026-01-12T08:00");
  const [termEndsDraft, setTermEndsDraft] = useState("2026-06-20T18:00");
  const [termStatusDraft, setTermStatusDraft] = useState("OPEN");
  const [termCreating, setTermCreating] = useState(false);
  const [termCreateError, setTermCreateError] = useState<string | null>(null);
  const selectedTerm = terms.find((t) => t.id === termId) ?? terms[0];
  const [cohortCode, setCohortCode] = useState("");
  const [admissionReference, setAdmissionReference] = useState("");
  const [admissionVerified, setAdmissionVerified] = useState(false);
  const [admissionVerifying, setAdmissionVerifying] = useState(false);
  const admissionRequestSequence = useRef(0);

  // Identity + credentials draft
  const [firstName, setFirstName] = useState("");
  const [middleNames, setMiddleNames] = useState("");
  const [firstSurname, setFirstSurname] = useState("");
  const [secondSurname, setSecondSurname] = useState("");
  const [preferredName, setPreferredName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [email, setEmail] = useState("");
  const [studentNumber, setStudentNumber] = useState("");
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [assignment, setAssignment] = useState<AdminAssignmentPreview | null>(null);
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const assignmentRequestSequence = useRef(0);
  const [admissionVerificationVersion, setAdmissionVerificationVersion] = useState(0);

  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const wizardPanelRef = useRef<HTMLDivElement>(null);

  const filteredEnrollments = useMemo(() => {
    if (statusFilter === "ALL") return enrollments;
    return enrollments.filter((e) => e.status === statusFilter);
  }, [enrollments, statusFilter]);

  function invalidateAdmissionVerification() {
    admissionRequestSequence.current += 1;
    setAdmissionVerified(false);
    setAdmissionVerifying(false);
  }

  async function verifyAdmission() {
    if (!activeProgram?.id || !selectedTerm?.id || !admissionReference.trim()) return;
    const sequence = ++admissionRequestSequence.current;
    setError(null);
    setAdmissionVerifying(true);
    const result = await verifyAdminAdmissionFact({
      program_id: activeProgram.id,
      admission_term_id: selectedTerm.id,
      record_reference: admissionReference.trim(),
    });
    if (sequence !== admissionRequestSequence.current) return;
    setAdmissionVerifying(false);
    if (!result.data) {
      const friendly = friendlyAdmissionError(result.failure?.problem?.detail);
      setFieldErrors((p) => ({ ...p, admissionReference: friendly }));
      return;
    }
    setAdmissionVerified(true);
    setFieldErrors((p) => {
      const n = { ...p };
      delete n.admissionReference;
      return n;
    });
    setAssignment(null);
    setAdmissionVerificationVersion((c) => c + 1);
    setMessage("Acta de admisión encontrada y sellada. Se usará para la asignación automática.");
  }

  async function loadEnrollments(nextOffset: number, nextSearch = search) {
    const sequence = ++searchRequestSequence.current;
    setSearching(true);
    setError(null);
    const result = await getAdminEnrollments({
      search: nextSearch.trim() || undefined,
      limit: initialPage.limit,
      offset: nextOffset,
    });
    if (sequence !== searchRequestSequence.current) return;
    if (!result.data) {
      setError(result.failure?.problem?.detail ?? "No fue posible consultar las matrículas.");
      setSearching(false);
      return;
    }
    setEnrollments(result.data.items);
    setTotal(result.data.total);
    setPage(result.data);
    setSearching(false);
  }

  useEffect(() => {
    if (initialSearchRender.current) {
      initialSearchRender.current = false;
      return;
    }
    const timeout = window.setTimeout(() => void loadEnrollments(0, search), 300);
    return () => window.clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  // Auto-expand term creator when no periods exist — the blocker the user reported
  useEffect(() => {
    if (wizardOpen && wizardStep === 0 && terms.length === 0) setShowTermCreator(true);
  }, [wizardOpen, wizardStep, terms.length]);

  // Live curriculum assignment preview whenever wizard context changes
  useEffect(() => {
    if (!wizardOpen) return;
    if (!activeProgram?.id || !selectedTerm?.id) {
      queueMicrotask(() => setAssignment(null));
      return;
    }
    const seq = ++assignmentRequestSequence.current;
    const timeout = window.setTimeout(async () => {
      setAssignmentLoading(true);
      const result = await previewAdminCurriculumAssignment({
        program_id: activeProgram.id,
        admission_term_id: selectedTerm.id,
        context: "ADMISSION",
        cohort_code: cohortCode.trim(),
        admission_verification_method: admissionVerified ? "VERIFIED_ADMISSION_FACT" : "SOURCE_SNAPSHOT",
        admission_record_reference: admissionReference.trim() || null,
      });
      if (seq !== assignmentRequestSequence.current) return;
      setAssignmentLoading(false);
      if (!result.data) {
        setAssignment(null);
        // keep backend detail as muted error, not global banner
        return;
      }
      setAssignment(result.data);
    }, 280);
    return () => window.clearTimeout(timeout);
  }, [wizardOpen, activeProgram?.id, admissionReference, admissionVerificationVersion, admissionVerified, cohortCode, selectedTerm?.id]);

  // Keep term in sync when institution/program change — always guarantee a selectable period if one exists for the institution
  function chooseInstitution(nextId: string) {
    invalidateAdmissionVerification();
    setAssignment(null);
    setInstitutionId(nextId);
    const nextPrograms = liveCatalog.programs.filter((p) => p.institution_id === nextId);
    const nextProgram = nextPrograms[0];
    setProgramId(nextProgram?.id ?? "");
    const byInstitution = liveCatalog.terms.filter((t) => t.institution_id === nextId);
    const byCampus = nextProgram?.campus_id ? byInstitution.filter((t) => !t.campus_id || t.campus_id === nextProgram.campus_id) : byInstitution;
    const nextTerm = (byCampus.length ? byCampus : byInstitution)[0];
    setTermId(nextTerm?.id ?? "");
  }
  function chooseProgram(nextId: string) {
    invalidateAdmissionVerification();
    setAssignment(null);
    setProgramId(nextId);
    const nextProgram = liveCatalog.programs.find((p) => p.id === nextId);
    if (!nextProgram) return;
    const byInstitution = liveCatalog.terms.filter((t) => t.institution_id === nextProgram.institution_id);
    const byCampus = nextProgram.campus_id ? byInstitution.filter((t) => !t.campus_id || t.campus_id === nextProgram.campus_id) : byInstitution;
    const nextTerm = (byCampus.length ? byCampus : byInstitution)[0];
    setTermId(nextTerm?.id ?? "");
  }

  async function handleCreateTerm() {
    if (!institutionId) { setTermCreateError("Selecciona una institución primero."); return; }
    if (!termCodeDraft.trim()) { setTermCreateError("El código es obligatorio (ej. 2026-1S)."); return; }
    if (!termStartsDraft || !termEndsDraft) { setTermCreateError("Define inicio y fin del período."); return; }
    const starts = new Date(termStartsDraft);
    const ends = new Date(termEndsDraft);
    if (Number.isNaN(starts.getTime()) || Number.isNaN(ends.getTime()) || starts >= ends) {
      setTermCreateError("Las fechas son inválidas o el inicio es posterior al fin.");
      return;
    }
    setTermCreating(true);
    setTermCreateError(null);
    const campusId = activeProgram?.campus_id ?? null;
    const result = await createAcademicTerm({
      institution_id: institutionId,
      campus_id: campusId,
      code: termCodeDraft.trim(),
      starts_at: starts.toISOString(),
      ends_at: ends.toISOString(),
      status: termStatusDraft,
    } as any);
    setTermCreating(false);
    if (!result.data) {
      setTermCreateError(result.failure?.problem?.detail ?? "No se pudo crear el período. Revisa permisos (requiere ADMIN).");
      return;
    }
    // Refresh live catalog from backend to get canonical AdminTermView
    const refreshed = await getStudentAdminCatalog();
    if (refreshed.data) setLiveCatalog(refreshed.data);
    else {
      // Fallback local push if refresh fails
      const adminTerm = {
        id: (result.data as unknown as { id: string }).id,
        institution_id: institutionId,
        campus_id: campusId,
        code: termCodeDraft.trim(),
        status: termStatusDraft,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
        admission_source_status: "UNKNOWN",
      } as StudentAdminCatalog["terms"][number];
      setLiveCatalog((prev) => ({ ...prev, terms: [...prev.terms, adminTerm] }));
    }
    setTermId((result.data as unknown as { id: string }).id);
    setShowTermCreator(false);
    setMessage(`Período ${termCodeDraft.trim()} creado. Ya puedes seleccionar el período de ingreso.`);
  }

  function validateStep(step: number): boolean {
    const errors: Record<string, string> = {};
    if (step === 0) {
      if (!institutionId) errors.institution = "Selecciona una institución.";
      if (!activeProgram) errors.program = "Selecciona un programa.";
      if (!selectedTerm) errors.term = "Selecciona un período de ingreso.";
    }
    if (step === 1) {
      if (!firstName.trim()) errors.first_name = "El primer nombre es obligatorio.";
      if (!firstSurname.trim()) errors.first_surname = "El primer apellido es obligatorio.";
      if (!birthDate) errors.birth_date = "La fecha de nacimiento es obligatoria.";
      else {
        const d = new Date(birthDate);
        const now = new Date();
        if (Number.isNaN(d.getTime())) errors.birth_date = "Fecha no válida.";
        else if (d > now) errors.birth_date = "No puede ser una fecha futura.";
        else if (d.getFullYear() < 1900) errors.birth_date = "Fecha fuera de rango.";
      }
    }
    if (step === 2) {
      if (!email.trim()) errors.email = "El correo es obligatorio.";
      else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) errors.email = "Correo no válido.";
      if (!studentNumber.trim()) errors.student_number = "El número estudiantil es obligatorio.";
      if (!temporaryPassword) errors.temporary_password = "La contraseña temporal es obligatoria.";
      else if (temporaryPassword.length < 12) errors.temporary_password = "Mínimo 12 caracteres.";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function nextStep() {
    if (!validateStep(wizardStep)) return;
    setWizardStep((s) => Math.min(3, s + 1));
  }
  function prevStep() {
    setWizardStep((s) => Math.max(0, s - 1));
    setFieldErrors({});
  }

  function resetWizard() {
    setWizardStep(0);
    setCohortCode("");
    setAdmissionReference("");
    invalidateAdmissionVerification();
    setAssignment(null);
    setFirstName("");
    setMiddleNames("");
    setFirstSurname("");
    setSecondSurname("");
    setPreferredName("");
    setBirthDate("");
    setEmail("");
    setStudentNumber("");
    setTemporaryPassword("");
    setShowPassword(false);
    setFieldErrors({});
    setShowTermCreator(false);
    setTermCreateError(null);
    setTermCodeDraft("2026-1S");
    setTermStatusDraft("OPEN");
  }

  function openWizard() {
    resetWizard();
    // re-anchor to current live catalog selection
    const inst = firstId(liveCatalog.institutions);
    const prog = liveCatalog.programs.find((p) => p.institution_id === inst) ?? liveCatalog.programs[0];
    if (inst) setInstitutionId(inst);
    if (prog) setProgramId(prog.id);
    const byInstitution = liveCatalog.terms.filter((term) => term.institution_id === inst);
    const byCampus = prog?.campus_id ? byInstitution.filter((term) => !term.campus_id || term.campus_id === prog.campus_id) : byInstitution;
    const t = (byCampus.length ? byCampus : byInstitution)[0];
    if (t) setTermId(t.id);
    setWizardOpen(true);
    setTimeout(() => wizardPanelRef.current?.querySelector<HTMLElement>("input,select,button")?.focus(), 80);
  }

  function closeWizard() {
    setWizardOpen(false);
    setError(null);
    setFieldErrors({});
  }

  async function submitCreation() {
    if (!validateStep(0) || !validateStep(1) || !validateStep(2)) {
      setWizardStep(0);
      return;
    }
    if (!institutionId || !activeProgram || !selectedTerm) {
      setError("Completa el programa y el período de ingreso.");
      return;
    }
    if (!assignment) {
      setError("Espera a que termine la evaluación de la política curricular.");
      return;
    }
    const payload: AdminEnrollmentCreatePayload = {
      email: email.trim(),
      temporary_password: temporaryPassword,
      first_name: firstName.trim(),
      middle_names: middleNames.trim(),
      first_surname: firstSurname.trim(),
      second_surname: secondSurname.trim(),
      preferred_name: preferredName.trim(),
      birth_date: birthDate,
      student_number: studentNumber.trim(),
      cohort_code: cohortCode.trim(),
      institution_id: institutionId,
      program_id: activeProgram.id,
      admission_term_id: selectedTerm.id,
      assignment_context: "ADMISSION",
      expected_assignment_hash: assignment.decision_hash,
      admission_verification_method: admissionVerified ? "VERIFIED_ADMISSION_FACT" : "SOURCE_SNAPSHOT",
      admission_record_reference: admissionReference.trim(),
    };
    startTransition(async () => {
      setError(null);
      const result = await createAdminEnrollment(payload);
      if (!result.data) {
        setError(result.failure?.problem?.detail ?? "No fue posible crear la cuenta y la matrícula.");
        return;
      }
      setWizardOpen(false);
      setSearch("");
      await loadEnrollments(0, "");
      setMessage(
        result.data.status === "ACTIVE"
          ? `Cuenta y matrícula creadas para ${result.data.display_name}.`
          : `Cuenta creada para ${result.data.display_name}; la matrícula quedó pendiente de política curricular verificada.`,
      );
      resetWizard();
    });
  }

  const termStatusLabel = (s: string) => ({ OPEN: "Abierto", PLANNED: "Planeado", CLOSED: "Cerrado", COMPLETED: "Finalizado" })[s] ?? "Estado no reconocido";
  const enrollmentStatusLabel = (s: string) => ({ ACTIVE: "Activa", COMPLETED: "Finalizada", WITHDRAWN: "Retirada", SUSPENDED: "Suspendida", NEEDS_REVIEW: "Requiere revisión", TRANSITIONED: "Transicionada" })[s] ?? "Estado no reconocido";
  const totalPages = Math.max(1, Math.ceil(total / page.limit));
  const currentPage = Math.floor(page.offset / page.limit) + 1;
  const rangeFrom = total === 0 ? 0 : page.offset + 1;
  const rangeTo = Math.min(total, page.offset + page.limit);

  // ESC to close wizard
  useEffect(() => {
    if (!wizardOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeWizard();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [wizardOpen]);

  return (
    <div className="student-admin-workspace">
      <header className="student-admin-hero">
        <div className="student-admin-hero__copy">
          <p className="eyebrow accent">Administración académica</p>
          <h1>Estudiantes y matrículas</h1>
          <p>Alta verificada, auditoría completa y trazabilidad de asignación curricular. Cada matrícula conserva su hecho individual de admisión y su decisión gobernada.</p>
        </div>
        <div className="student-admin-hero__actions">
          <div className="student-admin-hero__stats" aria-label="Resumen de matrículas">
            <span>
              <strong>{total}</strong> registros
            </span>
            <span aria-hidden="true">·</span>
            <span>
              {filteredEnrollments.length} visibles
            </span>
          </div>
          <button type="button" className="button button-primary student-admin-cta" onClick={openWizard}>
            <span aria-hidden="true">＋</span> Nuevo estudiante
          </button>
        </div>
      </header>

      {message ? (
        <div className="student-admin-toast" role="status" aria-live="polite">
          <Alert tone="success">
            {message}{" "}
            <button type="button" className="button button-quiet" onClick={() => setMessage(null)} aria-label="Cerrar notificación">
              Cerrar
            </button>
          </Alert>
        </div>
      ) : null}
      {error && !wizardOpen ? <Alert tone="error">{error}</Alert> : null}

      <section className="panel student-admin-list" aria-labelledby="managed-students-title">
        <div className="student-admin-toolbar">
          <label className="student-admin-search" aria-label="Buscar matrículas">
            <span className="sr-only">Buscar</span>
            <span aria-hidden="true" className="student-admin-search__icon">
              ⌕
            </span>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, correo o número…"
              aria-label="Buscar"
            />
            {search ? (
              <button type="button" className="student-admin-search__clear" aria-label="Limpiar búsqueda" onClick={() => setSearch("")}>
                ×
              </button>
            ) : null}
          </label>
          <div className="student-admin-filters" role="group" aria-label="Filtros">
            <label className="field-group field-group--inline">
              <span>Estado</span>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}>
                <option value="ALL">Todos</option>
                <option value="ACTIVE">Activa</option>
                <option value="NEEDS_REVIEW">En revisión</option>
              </select>
            </label>
            <span className="student-admin-count" aria-live="polite">
              {searching ? "Buscando…" : `${rangeFrom}–${rangeTo} de ${total}`}
            </span>
          </div>
        </div>

        <div className="section-heading section-heading--compact">
          <h2 id="managed-students-title">
            {statusFilter === "ALL" ? "Matrículas registradas" : statusFilter === "ACTIVE" ? "Matrículas activas" : "Matrículas en revisión"} · {filteredEnrollments.length}
          </h2>
          <span className="muted-copy">
            Página {currentPage} de {totalPages}
          </span>
        </div>

        {searching ? (
          <div className="student-admin-skeletons" role="status" aria-label="Cargando matrículas">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="student-card student-card--skeleton">
                <span className="skeleton skeleton-avatar" />
                <div>
                  <span className="skeleton skeleton-line" style={{ width: "14rem" }} />
                  <span className="skeleton skeleton-line" style={{ width: "10rem" }} />
                </div>
              </div>
            ))}
          </div>
        ) : filteredEnrollments.length ? (
          <div className="student-admin-grid">
            {filteredEnrollments.map((enrollment) => (
              <article key={enrollment.id} className="student-card">
                <div className="student-card__header">
                  <span className="student-card__avatar" aria-hidden="true">
                    {initialsFrom(enrollment.display_name, enrollment.email)}
                  </span>
                  <div className="student-card__identity">
                    <strong title={enrollment.display_name || enrollment.email}>{enrollment.display_name || enrollment.email}</strong>
                    <span>
                      {enrollment.student_number || "Sin número"} · {enrollment.email}
                    </span>
                    <small>
                      {enrollment.program_name} · {enrollment.plan_code ? `Plan ${enrollment.plan_code}` : "Plan pendiente de verificación"} · ingreso {enrollment.admission_term_code}
                    </small>
                  </div>
                  <div className="student-card__badges">
                    <StatusBadge tone={enrollment.status === "ACTIVE" ? "eligible" : enrollment.status === "NEEDS_REVIEW" ? "unknown" : "neutral"} label={enrollmentStatusLabel(enrollment.status)} />
                    {enrollment.identity_data_status === "LEGACY_UNSTRUCTURED" ? <StatusBadge tone="unknown" label="Identidad por confirmar" /> : null}
                    {enrollment.review_reasons.includes("IDENTITY_REVIEW") ? <StatusBadge tone="blocked" label="Identidad en revisión" /> : null}
                  </div>
                </div>
                <div className="student-card__actions">
                  <IdentityRectification
                    enrollment={enrollment}
                    onUpdated={(updated) => {
                      setEnrollments((cur) => cur.map((it) => (it.id === updated.id ? updated : it)));
                      setMessage(`Identidad actualizada para ${updated.display_name}.`);
                    }}
                  />
                  {enrollment.status === "NEEDS_REVIEW" && enrollment.review_reasons.includes("CURRICULUM_ASSIGNMENT") ? (
                    <EnrollmentResolution
                      enrollment={enrollment}
                      catalog={catalog}
                      currentUserId={currentUserId}
                      onResolved={(updated) => {
                        setEnrollments((cur) => cur.map((it) => (it.id === updated.id ? updated : it)));
                        setMessage(`Asignación curricular verificada para ${updated.display_name}.`);
                      }}
                    />
                  ) : null}
                  {enrollment.plan_id ? (
                    <EnrollmentTransition
                      enrollment={enrollment}
                      catalog={catalog}
                      onCreated={(created) => {
                        setEnrollments((cur) => [created, ...cur]);
                        setTotal((c) => c + 1);
                        setMessage(`Nueva matrícula registrada para ${created.display_name}.`);
                      }}
                    />
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="student-admin-empty">
            <h3>Sin resultados</h3>
            <p className="muted-copy">
              {search || statusFilter !== "ALL"
                ? "No hay matrículas que coincidan con la búsqueda o el filtro. Ajusta los criterios o crea un nuevo registro."
                : "Aún no hay matrículas registradas. Crea el primer estudiante para iniciar el flujo operativo."}
            </p>
            <button type="button" className="button button-primary" onClick={openWizard}>
              Crear primer estudiante
            </button>
          </div>
        )}

        <nav className="pagination-controls" aria-label="Páginas de matrículas">
          <button type="button" className="button button-secondary" disabled={searching || page.previous_offset === null} onClick={() => void loadEnrollments(page.previous_offset ?? 0)}>
            Anterior
          </button>
          <span>
            Página {currentPage} de {totalPages} · {total} en total
          </span>
          <button type="button" className="button button-secondary" disabled={searching || page.next_offset === null} onClick={() => void loadEnrollments(page.next_offset ?? 0)}>
            Siguiente
          </button>
        </nav>
      </section>

      {wizardOpen ? (
        <div className="wizard-overlay" role="dialog" aria-modal="true" aria-labelledby="create-student-title" onClick={(e) => { if (e.target === e.currentTarget) closeWizard(); }}>
          <div className="wizard-panel panel" ref={wizardPanelRef}>
            <header className="wizard-header">
              <div>
                <p className="eyebrow accent">Alta completa · paso {wizardStep + 1} de 4</p>
                <h2 id="create-student-title">Crear estudiante</h2>
                <p className="muted-copy">Identidad estructurada + credenciales + vinculación académica sellada. La asignación curricular se evalúa en vivo contra políticas verificadas.</p>
              </div>
              <button type="button" className="icon-button" aria-label="Cerrar alta" onClick={closeWizard}>
                ×
              </button>
            </header>

            <ol className="wizard-stepper" aria-label="Progreso de alta">
              {[
                { label: "Contexto", hint: "Programa y período" },
                { label: "Identidad", hint: "Nombres y nacimiento" },
                { label: "Acceso", hint: "Correo y contraseña" },
                { label: "Revisión", hint: "Confirmar y crear" },
              ].map((step, idx) => (
                <li key={step.label} className={`wizard-step ${idx === wizardStep ? "wizard-step--active" : ""} ${idx < wizardStep ? "wizard-step--done" : ""}`} aria-current={idx === wizardStep ? "step" : undefined}>
                  <span className="wizard-step__index">{idx < wizardStep ? "✓" : idx + 1}</span>
                  <span className="wizard-step__label">
                    <strong>{step.label}</strong>
                    <small>{step.hint}</small>
                  </span>
                </li>
              ))}
            </ol>

            {error ? <Alert tone="error">{error}</Alert> : null}

            <div className="wizard-body">
              {wizardStep === 0 ? (
                <section aria-labelledby="wizard-context-title" className="wizard-section">
                  <h3 id="wizard-context-title">Contexto académico</h3>
                  <div className="wizard-grid wizard-grid--2">
                    <label className="field-group">
                      <span>Institución</span>
                      <select value={institutionId} onChange={(e) => chooseInstitution(e.target.value)} required>
                        {liveCatalog.institutions.map((inst) => (
                          <option key={inst.id} value={inst.id}>
                            {inst.name}
                          </option>
                        ))}
                      </select>
                      {fieldErrors.institution ? <small className="field-error">{fieldErrors.institution}</small> : null}
                    </label>
                    <label className="field-group">
                      <span>Programa y sede</span>
                      <select value={activeProgram?.id ?? ""} onChange={(e) => chooseProgram(e.target.value)} required>
                        {programs.length ? (
                          programs.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name} · {p.campus_name}
                            </option>
                          ))
                        ) : (
                          <option value="" disabled>
                            No hay programas — verifica el catálogo
                          </option>
                        )}
                      </select>
                      {programs.length === 0 ? <small className="field-error">No hay programas para esta institución. Revisa la configuración del catálogo.</small> : null}
                      {fieldErrors.program ? <small className="field-error">{fieldErrors.program}</small> : null}
                    </label>
                    <label className="field-group">
                      <span>Período de ingreso</span>
                      <select required value={termId} onChange={(e) => { invalidateAdmissionVerification(); setAssignment(null); setTermId(e.target.value); }}>
                        {terms.length ? (
                          terms.map((t) => (
                            <option key={t.id} value={t.id}>
                              {t.code} · {termStatusLabel(t.status)} · fuente {t.admission_source_status === "VERIFIED" ? "verificada" : "pendiente"}
                            </option>
                          ))
                        ) : (
                          <option value="" disabled>
                            No hay períodos disponibles — crea un período en Oferta académica
                          </option>
                        )}
                      </select>
                      {terms.length === 0 ? <small className="field-error">No hay períodos para esta institución. Crea un período antes de dar de alta.</small> : null}
                      {fieldErrors.term ? <small className="field-error">{fieldErrors.term}</small> : null}
                    </label>
                    <label className="field-group">
                      <span>Cohorte (opcional)</span>
                      <input value={cohortCode} onChange={(e) => { setAssignment(null); setCohortCode(e.target.value); }} placeholder="2026-1" />
                    </label>
                  </div>
                  {terms.length === 0 ? (
                    <Alert tone="warning">
                      No hay períodos de ingreso configurados. Crea el primer período aquí mismo para desbloquear el alta. También puedes gestionarlos en <a href="/offerings" className="text-link">Oferta académica → Ver fuente</a>.
                    </Alert>
                  ) : null}
                  {programs.length === 0 ? (
                    <Alert tone="warning">No hay programas visibles para tu alcance administrativo. Verifica que tengas rol ADMIN sobre la institución correcta.</Alert>
                  ) : null}

                  <div className="term-creator">
                    <button
                      type="button"
                      className="button button-secondary"
                      onClick={() => setShowTermCreator((v) => !v)}
                      aria-expanded={showTermCreator}
                    >
                      {showTermCreator ? "Cancelar creación de período" : terms.length === 0 ? "Crear primer período ahora" : "+ Crear nuevo período"}
                    </button>
                    {showTermCreator ? (
                      <div className="term-creator__form">
                        <p className="muted-copy">El período define el ingreso (código, fechas y estado). Queda auditable y se puede usar de inmediato para la matrícula. Requiere rol ADMIN.</p>
                        <div className="wizard-grid wizard-grid--2">
                          <label className="field-group">
                            <span>Código *</span>
                            <input value={termCodeDraft} onChange={(e) => setTermCodeDraft(e.target.value)} placeholder="2026-1S" />
                            <small>Ej. 2026-1S, 2026-2S. Debe ser único por institución.</small>
                          </label>
                          <label className="field-group">
                            <span>Estado</span>
                            <select value={termStatusDraft} onChange={(e) => setTermStatusDraft(e.target.value)}>
                              <option value="OPEN">Abierto</option>
                              <option value="PLANNED">Planeado</option>
                              <option value="CLOSED">Cerrado</option>
                            </select>
                          </label>
                          <label className="field-group">
                            <span>Inicia *</span>
                            <input type="datetime-local" value={termStartsDraft} onChange={(e) => setTermStartsDraft(e.target.value)} />
                          </label>
                          <label className="field-group">
                            <span>Termina *</span>
                            <input type="datetime-local" value={termEndsDraft} onChange={(e) => setTermEndsDraft(e.target.value)} />
                          </label>
                        </div>
                        {termCreateError ? <Alert tone="error">{termCreateError}</Alert> : null}
                        <div className="term-creator__actions">
                          <button type="button" className="button button-primary" disabled={termCreating} onClick={() => void handleCreateTerm()}>
                            {termCreating ? "Creando…" : `Crear período ${termCodeDraft || ""}`.trim()}
                          </button>
                          <small className="muted-copy">Se creará en {liveCatalog.institutions.find((i) => i.id === institutionId)?.name ?? "la institución seleccionada"}{activeProgram?.campus_name ? ` · campus ${activeProgram.campus_name}` : ""}.</small>
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="field-group">
                    <label htmlFor="admission-code-input">
                      <span>Código del acta de admisión <small style={{ fontWeight: 500, color: "var(--text-muted)" }}>(opcional)</small></span>
                    </label>
                    <div className="field-with-action">
                      <input
                        id="admission-code-input"
                        value={admissionReference}
                        onChange={(e) => {
                          invalidateAdmissionVerification();
                          setAssignment(null);
                          setAdmissionReference(e.target.value);
                        }}
                        placeholder="Ej: RES-2026-1234 o código SIA"
                        aria-describedby="admission-help admission-status"
                        autoComplete="off"
                      />
                      <button
                        type="button"
                        className="button button-secondary"
                        disabled={!activeProgram?.id || !selectedTerm?.id || !admissionReference.trim() || admissionVerified || admissionVerifying}
                        onClick={() => void verifyAdmission()}
                      >
                        {admissionVerifying ? "Verificando…" : admissionVerified ? "Verificada ✓" : "Verificar en archivo"}
                      </button>
                    </div>
                    <small id="admission-help">
                      Si tienes el acta o resolución SIA archivada en <a href="/sources" className="text-link">Fuentes</a>, pega el código exacto y verifica. Si no lo tienes, deja el campo vacío.
                    </small>
                    <div id="admission-status" aria-live="polite">
                      {!admissionReference.trim() && !admissionVerified ? (
                        <Alert tone="info">
                          Sin acta verificada → la matrícula se creará como <strong>Revisión pendiente</strong>. Podrás reevaluarla cuando la política y el acta estén publicadas.
                        </Alert>
                      ) : null}
                      {admissionReference.trim() && !admissionVerified && !admissionVerifying && !fieldErrors.admissionReference ? (
                        <Alert tone="warning">
                          Código escrito pero aún no verificado. Presiona <strong>Verificar en archivo</strong> o borra el código para continuar en revisión. Escribir el código sin verificar no habilita la asignación automática.
                        </Alert>
                      ) : null}
                      {admissionVerifying ? <p role="status" className="muted-copy">Buscando acta archivada para este programa y período…</p> : null}
                      {fieldErrors.admissionReference ? <Alert tone="error">{fieldErrors.admissionReference}</Alert> : null}
                      {admissionVerified ? (
                        <Alert tone="success">✓ Acta encontrada y sellada para {activeProgram?.name} · {selectedTerm?.code}. Se usará para decidir plan y revisión automáticamente.</Alert>
                      ) : null}
                    </div>
                    <details className="admission-technical">
                      <summary>¿Por qué menciona HMAC / sellado?</summary>
                      <p className="muted-copy">Por privacidad el código se guarda con HMAC y el acta queda sellada con su hash y localizador. No necesitas entenderlo para usar el formulario: solo pega el código y presiona Verificar.</p>
                    </details>
                  </div>
                  <div aria-live="polite" aria-busy={assignmentLoading} className="wizard-preview">
                    <AssignmentPreviewCard assignment={assignment} loading={assignmentLoading} />
                  </div>
                </section>
              ) : null}

              {wizardStep === 1 ? (
                <section aria-labelledby="wizard-identity-title" className="wizard-section">
                  <h3 id="wizard-identity-title">Identidad estructurada</h3>
                  <p className="muted-copy">Usa nombres legales. El nombre preferido es sólo trato personal. La fecha de nacimiento alimenta la edad derivada y queda auditada.</p>
                  <div className="wizard-grid wizard-grid--2">
                    <label className="field-group">
                      <span>Primer nombre *</span>
                      <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required autoComplete="given-name" placeholder="Ana" />
                      {fieldErrors.first_name ? <small className="field-error">{fieldErrors.first_name}</small> : null}
                    </label>
                    <label className="field-group">
                      <span>Otros nombres</span>
                      <input value={middleNames} onChange={(e) => setMiddleNames(e.target.value)} autoComplete="additional-name" placeholder="María" />
                    </label>
                    <label className="field-group">
                      <span>Primer apellido *</span>
                      <input value={firstSurname} onChange={(e) => setFirstSurname(e.target.value)} required autoComplete="family-name" placeholder="López" />
                      {fieldErrors.first_surname ? <small className="field-error">{fieldErrors.first_surname}</small> : null}
                    </label>
                    <label className="field-group">
                      <span>Segundo apellido</span>
                      <input value={secondSurname} onChange={(e) => setSecondSurname(e.target.value)} placeholder="Ruiz" />
                    </label>
                    <label className="field-group">
                      <span>Nombre preferido</span>
                      <input value={preferredName} onChange={(e) => setPreferredName(e.target.value)} placeholder="Ani" />
                      <small>No reemplaza el nombre académico.</small>
                    </label>
                    <label className="field-group">
                      <span>Fecha de nacimiento *</span>
                      <input value={birthDate} onChange={(e) => setBirthDate(e.target.value)} type="date" required autoComplete="bday" />
                      {fieldErrors.birth_date ? <small className="field-error">{fieldErrors.birth_date}</small> : <small>La edad se deriva, no se almacena duplicada.</small>}
                    </label>
                  </div>
                </section>
              ) : null}

              {wizardStep === 2 ? (
                <section aria-labelledby="wizard-credentials-title" className="wizard-section">
                  <h3 id="wizard-credentials-title">Credenciales de acceso</h3>
                  <div className="wizard-grid wizard-grid--2">
                    <label className="field-group">
                      <span>Correo de acceso *</span>
                      <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="off" placeholder="ana.lopez@unal.edu.co" />
                      {fieldErrors.email ? <small className="field-error">{fieldErrors.email}</small> : <small>El estudiante debe cambiarla en el primer ingreso.</small>}
                    </label>
                    <label className="field-group">
                      <span>Número estudiantil * — código SIA</span>
                      <input value={studentNumber} onChange={(e) => setStudentNumber(e.target.value)} required placeholder="202610001" aria-describedby="student-number-help" />
                      <small id="student-number-help">Código que el SIA asigna al estudiante. Se guarda cifrado con HMAC para verificar el hecho individual de admisión y debe ser único dentro de la institución.</small>
                      {fieldErrors.student_number ? <small className="field-error">{fieldErrors.student_number}</small> : null}
                    </label>
                    <label className="field-group field-group--full">
                      <span>Contraseña temporal *</span>
                      <div className="field-with-action">
                        <input value={temporaryPassword} onChange={(e) => setTemporaryPassword(e.target.value)} type={showPassword ? "text" : "password"} required minLength={12} autoComplete="new-password" placeholder="Mínimo 12 caracteres" />
                        <button type="button" className="button button-secondary" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}>
                          {showPassword ? "Ocultar" : "Mostrar"}
                        </button>
                      </div>
                      {fieldErrors.temporary_password ? <small className="field-error">{fieldErrors.temporary_password}</small> : <small>Compártela por un canal seguro; nunca se vuelve a mostrar en claro. Mínimo 12 caracteres.</small>}
                      {temporaryPassword ? <small className={temporaryPassword.length >= 12 ? "field-success" : "field-error"}>{temporaryPassword.length} / 12 caracteres</small> : null}
                    </label>
                  </div>
                </section>
              ) : null}

              {wizardStep === 3 ? (
                <section aria-labelledby="wizard-review-title" className="wizard-section">
                  <h3 id="wizard-review-title">Revisión y confirmación</h3>
                  <div className="wizard-review-grid">
                    <article className="wizard-review-card">
                      <h4>Identidad</h4>
                      <dl>
                        <dt>Nombre completo</dt>
                        <dd>{[firstName, middleNames, firstSurname, secondSurname].filter(Boolean).join(" ") || "—"}</dd>
                        <dt>Preferido</dt>
                        <dd>{preferredName || "—"}</dd>
                        <dt>Nacimiento</dt>
                        <dd>{birthDate || "—"}</dd>
                      </dl>
                    </article>
                    <article className="wizard-review-card">
                      <h4>Acceso</h4>
                      <dl>
                        <dt>Correo</dt>
                        <dd>{email || "—"}</dd>
                        <dt>Número</dt>
                        <dd>{studentNumber || "—"}</dd>
                        <dt>Contraseña</dt>
                        <dd>{temporaryPassword ? "•".repeat(Math.min(12, temporaryPassword.length)) : "—"}</dd>
                      </dl>
                    </article>
                    <article className="wizard-review-card">
                      <h4>Vinculación</h4>
                      <dl>
                        <dt>Institución</dt>
                        <dd>{liveCatalog.institutions.find((i) => i.id === institutionId)?.name ?? "—"}</dd>
                        <dt>Programa</dt>
                        <dd>{activeProgram ? `${activeProgram.name} · ${activeProgram.campus_name}` : "—"}</dd>
                        <dt>Período</dt>
                        <dd>{selectedTerm ? `${selectedTerm.code} · ${termStatusLabel(selectedTerm.status)}` : "—"}</dd>
                        <dt>Cohorte</dt>
                        <dd>{cohortCode.trim() || "—"}</dd>
                        <dt>Referencia</dt>
                        <dd>{admissionReference.trim() || "—"} {admissionVerified ? "(verificada)" : "(no verificada)"}</dd>
                      </dl>
                    </article>
                  </div>
                  <div aria-live="polite">
                    <AssignmentPreviewCard assignment={assignment} loading={assignmentLoading} />
                  </div>
                  {!assignment ? <Alert tone="warning">Espera a que termine la evaluación de la política curricular antes de crear.</Alert> : null}
                  {assignment && assignment.status !== "RESOLVED" ? (
                    <Alert tone="warning">
                      La matrícula se creará en estado <strong>Requiere revisión</strong> porque no hay una única política verificada. Podrás resolverla cuando exista evidencia.
                    </Alert>
                  ) : null}
                </section>
              ) : null}
            </div>

            <footer className="wizard-footer">
              <div className="wizard-footer__left">
                <button type="button" className="button button-secondary" onClick={closeWizard}>
                  Cancelar
                </button>
              </div>
              <div className="wizard-footer__right">
                {wizardStep > 0 ? (
                  <button type="button" className="button button-secondary" onClick={prevStep}>
                    Atrás
                  </button>
                ) : null}
                {wizardStep < 3 ? (
                  <button type="button" className="button button-primary" onClick={nextStep}>
                    Continuar
                  </button>
                ) : (
                  <button type="button" className="button button-primary" disabled={pending || assignmentLoading || !assignment} onClick={() => void submitCreation()}>
                    {pending ? "Creando…" : assignment?.status === "RESOLVED" ? "Crear cuenta y matrícula" : "Crear con revisión pendiente"}
                  </button>
                )}
              </div>
            </footer>
          </div>
        </div>
      ) : null}
    </div>
  );
}
