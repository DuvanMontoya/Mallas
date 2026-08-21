"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  CalendarDays,
  CheckCircle2,
  Compass,
  FileText,
  GraduationCap,
  Scale,
} from "lucide-react";

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
  const configuredSteps = [
    identityConfirmed,
    historyStatus !== "PENDING",
    Boolean(termId),
    Number.isFinite(loadTarget) && loadTarget >= 1 && loadTarget <= 30,
    tourStatus !== "PENDING",
  ].filter(Boolean).length;
  const progressValue = Math.round((configuredSteps / 5) * 100);

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
        router.replace("/curriculum");
        router.refresh();
      }
    });
  }

  return (
    <div className="onboarding-workspace">
      <header className="onboarding-hero">
        <div className="onboarding-hero__copy">
          <p className="eyebrow accent">Primera sesión</p>
          <h1>Prepara tu espacio académico</h1>
          <p>Define sólo lo necesario para que las próximas decisiones tengan contexto. Puedes volver a ajustar estas preferencias cuando quieras.</p>
        </div>
        <div className="onboarding-progress" aria-label={`${configuredSteps} de 5 decisiones iniciales configuradas`}>
          <div className="onboarding-progress__topline"><span>Configuración inicial</span><strong>{configuredSteps}/5</strong></div>
          <div className="onboarding-progress__track" aria-hidden="true"><span style={{ width: `${progressValue}%` }} /></div>
          <p>Sin alterar tu plan oficial ni completar datos que no hayas confirmado.</p>
        </div>
      </header>

      <section className="onboarding-context" aria-labelledby="assigned-program-title">
        <div className="onboarding-context__identity">
          <span className="onboarding-context__icon" aria-hidden="true"><GraduationCap size={23} /></span>
          <div><p className="eyebrow">Tu vinculación</p><h2 id="assigned-program-title">{state.program_name}</h2><p>Ingreso {state.admission_term_code}</p></div>
        </div>
        {assignmentResolved ? (
          <div className="onboarding-assignment onboarding-assignment--resolved"><CheckCircle2 size={19} aria-hidden="true" /><div><strong>Plan {state.plan_code} · revisión {state.revision_code}</strong><p>Tu malla personal estará disponible cuando termines esta configuración.</p></div></div>
        ) : (
          <div className="onboarding-assignment onboarding-assignment--review"><Scale size={19} aria-hidden="true" /><div><strong>Plan pendiente de verificación</strong><p>No mostraremos avance, elegibilidad o faltantes como definitivos hasta contar con una política aplicable. Motivo: {state.assignment_reason_codes.join(", ") || "sin política aplicable"}.</p></div></div>
        )}
      </section>

      <form className="onboarding-form" onSubmit={(event) => { event.preventDefault(); save(true); }}>
        <aside className="onboarding-nav" aria-label="Decisiones de configuración">
          <p className="eyebrow">Tu recorrido</p>
          <ol>
            {[
              ["Identidad", identityConfirmed],
              ["Historia", historyStatus !== "PENDING"],
              ["Período", Boolean(termId)],
              ["Preferencia", Number.isFinite(loadTarget) && loadTarget >= 1 && loadTarget <= 30],
              ["Malla", tourStatus !== "PENDING"],
            ].map(([label, done], index) => <li key={String(label)} className={done ? "is-complete" : ""}><span>{done ? <CheckCircle2 size={15} aria-hidden="true" /> : index + 1}</span>{label}</li>)}
          </ol>
          <p>Los estados personales sólo se calculan con una vinculación y una historia verificables.</p>
        </aside>
        <div className="onboarding-checklist">
          <fieldset className="onboarding-step">
            <legend><span>01</span> Confirma tu identidad</legend>
            <div className="onboarding-step__body"><BookOpenCheck size={20} aria-hidden="true" /><div><label className="check-row"><input type="checkbox" checked={identityConfirmed} onChange={(event) => setIdentityConfirmed(event.target.checked)} /><span>Revisé mis nombres y apellidos</span></label><p>Esta confirmación reconoce lo que está registrado; no modifica tu identidad.</p><Link className="text-link" href="/profile">Abrir mis datos de identidad <ArrowRight size={14} aria-hidden="true" /></Link></div></div>
          </fieldset>
          <fieldset className="onboarding-step">
            <legend><span>02</span> Decide cómo iniciar tu historia</legend>
            <div className="onboarding-step__body"><FileText size={20} aria-hidden="true" /><div><label className="field-group"><span>Historia académica</span><select required value={historyStatus} onChange={(event) => setHistoryStatus(event.target.value)}><option value="PENDING" disabled>Elige una opción</option><option value="SKIPPED">La completaré después</option><option value="IMPORTED">Ya fue importada o registrada</option></select><small>Omitirla no bloquea la malla; sólo deja los estados personales sin calcular.</small></label><Link className="text-link" href="/history">Revisar historia <ArrowRight size={14} aria-hidden="true" /></Link></div></div>
          </fieldset>
          <fieldset className="onboarding-step">
            <legend><span>03</span> Elige tu período actual</legend>
            <div className="onboarding-step__body"><CalendarDays size={20} aria-hidden="true" /><div>{termsFailure ? <Alert tone="error">{termsFailure} <a className="text-link" href="/onboarding">Reintentar</a></Alert> : null}<label className="field-group"><span>Período</span><select required value={termId} onChange={(event) => setTermId(event.target.value)} disabled={terms.length === 0}><option value="" disabled>{terms.length ? "Elige un período" : "No hay períodos disponibles"}</option>{terms.map((term) => <option key={term.id} value={term.id}>{term.code} · {term.status}</option>)}</select><small>Usaremos este período sólo como contexto para tus escenarios de planificación.</small></label></div></div>
          </fieldset>
          <fieldset className="onboarding-step">
            <legend><span>04</span> Define una referencia de carga</legend>
            <div className="onboarding-step__body"><Compass size={20} aria-hidden="true" /><div><label className="field-group onboarding-load-field"><span>Créditos objetivo por período</span><input type="number" min={1} max={30} value={loadTarget} onChange={(event) => setLoadTarget(Number(event.target.value))} required /><small>Es una preferencia de planificación, no una recomendación ni una inscripción.</small></label></div></div>
          </fieldset>
          <fieldset className="onboarding-step onboarding-step--tour">
            <legend><span>05</span> Familiarízate con la malla</legend>
            <div className="onboarding-step__body"><GraduationCap size={20} aria-hidden="true" /><div><div className="onboarding-mini-tour" aria-label="Leyenda básica de la malla"><p><strong>Aprobado</strong><span>Ya superaste el curso o requisito.</span></p><p><strong>Disponible</strong><span>Puedes cursarlo según reglas verificadas.</span></p><p><strong>Bloqueado o desconocido</strong><span>Abre el detalle para ver la causa y su evidencia.</span></p></div><label className="field-group"><span>Decisión sobre el recorrido</span><select required value={tourStatus} onChange={(event) => setTourStatus(event.target.value)}><option value="PENDING" disabled>Elige una opción después de leer la leyenda</option><option value="COMPLETED">Leí y entendí la leyenda básica</option><option value="SKIPPED">Prefiero repetir el recorrido después</option></select><small>Podrás abrir la ayuda de la malla cuando quieras.</small></label></div></div>
          </fieldset>
        </div>
        {error ? <Alert tone="error">{error}</Alert> : null}
        <footer className="onboarding-actions"><div><strong>Todo queda editable</strong><p>Guardar no publica, inscribe ni cambia tu currículo.</p></div><div className="form-actions"><button className="button button-secondary" type="button" disabled={pending || !requiredChoicesMade} onClick={() => save(false)}>Guardar y continuar después</button><button className="button button-primary" type="submit" disabled={pending || !requiredChoicesMade || !identityConfirmed}>{pending ? "Guardando…" : <>Terminar y abrir mi espacio <ArrowRight size={16} aria-hidden="true" /></>}</button></div></footer>
      </form>
    </div>
  );
}
