"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import {
  updateStudentOnboarding,
  type AcademicTerm,
  type StudentOnboardingView,
} from "@/lib/api";

import { Alert } from "./ui/alert";

export function StudentOnboardingForm({
  initial,
  terms,
  termsFailure = null,
}: {
  initial: StudentOnboardingView;
  terms: AcademicTerm[];
  termsFailure?: string | null;
}) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [identityConfirmed, setIdentityConfirmed] = useState(initial.identity_confirmed);
  const [historyStatus, setHistoryStatus] = useState(initial.history_step_status);
  const [termId, setTermId] = useState(initial.current_term_id ?? terms[0]?.id ?? "");
  const [loadTarget, setLoadTarget] = useState(initial.planning_load_target ?? 16);
  const [tourStatus, setTourStatus] = useState(initial.tour_status);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const assignmentResolved = Boolean(state.plan_code && state.revision_code);
  const requiredChoicesMade = Boolean(
    termId && historyStatus !== "PENDING" && tourStatus !== "PENDING",
  );

  function save(complete: boolean) {
    setError(null);
    startTransition(async () => {
      const result = await updateStudentOnboarding(
        {
          identity_confirmed: identityConfirmed,
          history_step_status: historyStatus,
          current_term_id: termId,
          planning_load_target: loadTarget,
          tour_status: tourStatus,
          complete,
        },
        state.version,
      );
      if (!result.data) {
        setError(result.failure?.problem?.detail ?? "No fue posible guardar tu configuración inicial.");
        return;
      }
      setState(result.data);
      if (result.data.completed) {
        router.replace(result.data.plan_code && result.data.revision_code ? "/curriculum" : "/");
        router.refresh();
      }
    });
  }

  return (
    <div className="onboarding-workspace">
      <header className="route-command">
        <div><p className="eyebrow accent">Primera sesión</p><h1>Prepara tu espacio académico</h1><p>Estas decisiones son reanudables. No cambian tu plan oficial ni inventan datos de tu historia.</p></div>
      </header>

      <section className="panel onboarding-program" aria-labelledby="assigned-program-title">
        <div><p className="eyebrow">Tu vinculación</p><h2 id="assigned-program-title">{state.program_name}</h2><p>Ingreso {state.admission_term_code}</p></div>
        {assignmentResolved ? (
          <Alert tone="success"><strong>Plan {state.plan_code}</strong> · revisión {state.revision_code}. Tu malla personal estará disponible al terminar.</Alert>
        ) : (
          <Alert tone="warning"><strong>Plan pendiente de verificación.</strong> La cuenta ya existe, pero no mostraremos avance, elegibilidad o faltantes como definitivos. Motivos: {state.assignment_reason_codes.join(", ") || "sin política aplicable"}.</Alert>
        )}
      </section>

      <form className="panel onboarding-checklist" onSubmit={(event) => { event.preventDefault(); save(true); }}>
        <fieldset><legend>1. Confirma tu identidad</legend><label className="check-row"><input type="checkbox" checked={identityConfirmed} onChange={(event) => setIdentityConfirmed(event.target.checked)} /><span>Revisé mis nombres y apellidos</span></label><Link className="text-link" href="/profile">Abrir mis datos de identidad</Link></fieldset>
        <fieldset><legend>2. Decide cómo iniciar tu historia</legend><label className="field-group"><span>Historia académica</span><select required value={historyStatus} onChange={(event) => setHistoryStatus(event.target.value)}><option value="PENDING" disabled>Elige una opción</option><option value="SKIPPED">La completaré después</option><option value="IMPORTED">Ya fue importada o registrada</option></select><small>Omitirla no bloquea la malla; sólo deja los estados personales sin calcular.</small></label><Link className="text-link" href="/history">Revisar historia</Link></fieldset>
        <fieldset><legend>3. Elige tu período actual</legend>{termsFailure ? <Alert tone="error">{termsFailure} <a className="text-link" href="/onboarding">Reintentar</a></Alert> : null}<label className="field-group"><span>Período</span><select required value={termId} onChange={(event) => setTermId(event.target.value)} disabled={terms.length === 0}><option value="" disabled>{terms.length ? "Elige un período" : "No hay períodos disponibles"}</option>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · {term.status}</option>)}</select></label></fieldset>
        <fieldset><legend>4. Define una referencia de carga</legend><label className="field-group"><span>Créditos objetivo por período</span><input type="number" min={1} max={30} value={loadTarget} onChange={(event) => setLoadTarget(Number(event.target.value))} required /><small>Es una preferencia de planificación, no una recomendación ni una inscripción.</small></label></fieldset>
        <fieldset><legend>5. Recorrido visual</legend><div className="onboarding-mini-tour" aria-label="Leyenda básica de la malla"><p><strong>Aprobado:</strong> ya superaste el curso o requisito.</p><p><strong>Disponible:</strong> puedes cursarlo según las reglas verificadas.</p><p><strong>Bloqueado o desconocido:</strong> abre el detalle para ver la causa y su evidencia.</p></div><label className="field-group"><span>Decisión sobre el recorrido</span><select required value={tourStatus} onChange={(event) => setTourStatus(event.target.value)}><option value="PENDING" disabled>Elige una opción después de leer la leyenda</option><option value="COMPLETED">Leí y entendí la leyenda básica</option><option value="SKIPPED">Prefiero repetir el recorrido después</option></select><small>Podrás abrir la ayuda de la malla cuando quieras.</small></label></fieldset>
        {error ? <Alert tone="error">{error}</Alert> : null}
        <div className="form-actions"><button className="button button-secondary" type="button" disabled={pending || !requiredChoicesMade} onClick={() => save(false)}>Guardar estas decisiones y continuar después</button><button className="button button-primary" type="submit" disabled={pending || !requiredChoicesMade || !identityConfirmed}>{pending ? "Guardando…" : "Terminar y abrir mi espacio"}</button></div>
      </form>
    </div>
  );
}
