"use client";

import { useEffect, useMemo, useState } from "react";
import { CircleStop, Sparkles } from "lucide-react";

import {
  cancelOptimizationRun,
  getOptimizationRun,
  startOptimization,
  type OptimizationRun,
  type PlanningScenario,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge, type StatusTone } from "./ui/status-badge";

type ProposedCourse = {
  course_code: string;
  term_code: string;
  credits?: number | null;
  selected_section_id?: string | null;
};

function statusTone(status: string): StatusTone {
  if (status === "OPTIMAL") return "eligible";
  if (status === "FEASIBLE") return "unknown";
  if (status === "INFEASIBLE") return "blocked";
  if (status === "UNKNOWN") return "unknown";
  return "neutral";
}

function optimizationLabel(status: string) {
  return ({ QUEUED: "En espera", RUNNING: "Calculando", OPTIMAL: "Ruta encontrada", FEASIBLE: "Ruta posible", INFEASIBLE: "Sin ruta compatible", UNKNOWN: "No se pudo concluir", CANCELLED: "Cancelada", FAILED: "No se pudo calcular" } as Record<string, string>)[status] ?? status.replaceAll("_", " ").toLocaleLowerCase("es-CO");
}

function assumptionLabel(value: unknown) {
  return ({ UNKNOWN_OFFERINGS_ALLOWED: "Se permitieron períodos cuya oferta aún no está publicada" } as Record<string, string>)[String(value)] ?? String(value).replaceAll("_", " ").toLocaleLowerCase("es-CO");
}

function explanationText(value: unknown, fallback: string) {
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (!value || typeof value !== "object") return fallback;
  const item = value as Record<string, unknown>;
  if (item.detail || item.message) return String(item.detail ?? item.message);
  if (item.course_code && item.term_code) return `${String(item.course_code)} · ${String(item.term_code)}`;
  if (item.code) return String(item.code).replaceAll("_", " ").toLocaleLowerCase("es-CO");
  return fallback;
}

function proposedCourses(run: OptimizationRun | null): ProposedCourse[] {
  const selected = run?.solution?.selected_courses;
  return Array.isArray(selected) ? selected.filter((item): item is ProposedCourse => {
    return Boolean(item && typeof item === "object" && "course_code" in item && "term_code" in item);
  }) : [];
}

export function OptimizerPanel({ scenario }: { scenario: PlanningScenario }) {
  const [run, setRun] = useState<OptimizationRun | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!run || !["QUEUED", "RUNNING"].includes(run.status)) return;
    const timer = window.setTimeout(async () => {
      const result = await getOptimizationRun(run.id);
      if (result.data) setRun(result.data);
      if (result.failure) setMessage(result.failure.problem?.detail ?? "No se pudo consultar el optimizador.");
    }, 500);
    return () => window.clearTimeout(timer);
  }, [run]);

  const solution = useMemo(() => proposedCourses(run), [run]);
  const current = useMemo(
    () => new Map(scenario.planned_courses.map((course) => [course.course_code, course.term_code])),
    [scenario.planned_courses],
  );
  const proposed = useMemo(() => new Map(solution.map((course) => [course.course_code, course.term_code])), [solution]);
  const moved = solution.filter((course) => current.has(course.course_code) && current.get(course.course_code) !== course.term_code);
  const added = solution.filter((course) => !current.has(course.course_code));
  const removed = scenario.planned_courses.filter((course) => !proposed.has(course.course_code));
  const running = Boolean(run && ["QUEUED", "RUNNING"].includes(run.status));

  async function optimize() {
    setPending(true);
    setMessage(null);
    const result = await startOptimization(scenario.id, {
      time_limit_seconds: 30,
      unknown_offering_policy: "ALLOW_UNKNOWN",
      random_seed: 0,
    });
    setPending(false);
    if (result.data) setRun(result.data);
    if (result.failure) setMessage(result.failure.problem?.detail ?? "No se pudo iniciar la optimización.");
  }

  async function cancel() {
    if (!run) return;
    const result = await cancelOptimizationRun(run.id);
    if (result.data) setRun(result.data);
    if (result.failure) setMessage(result.failure.problem?.detail ?? "No se pudo cancelar la optimización.");
  }

  return (
    <section className="panel planner-optimizer-panel" aria-labelledby="planner-optimizer-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Ruta sugerida explicable</p>
          <h2 id="planner-optimizer-title">Optimiza este escenario</h2>
        </div>
        {run ? <StatusBadge tone={statusTone(run.status)} label={optimizationLabel(run.status)} /> : null}
      </div>
      <div className="planner-optimizer-actions">
        <button className="button button-primary" type="button" onClick={() => void optimize()} disabled={pending || running}>
          <Sparkles size={15} aria-hidden="true" /> {pending ? "Iniciando…" : "Optimizar ruta"}
        </button>
        {running ? <button className="button button-secondary" type="button" onClick={() => void cancel()}><CircleStop size={15} aria-hidden="true" /> Cancelar</button> : null}
      </div>
      {message ? <Alert tone="error">{message}</Alert> : null}
      {run && !running ? (
        <div className="planner-optimizer-result" aria-live="polite">
          <div className="planner-optimizer-facts"><span>Resultado <strong>{optimizationLabel(run.status)}</strong></span><details><summary>Trazabilidad técnica</summary><span>Versión <code>{run.solver_version}</code></span><span>Hash <code>{run.output_hash.slice(0, 12) || "—"}</code></span></details></div>
          {run.status === "INFEASIBLE" ? (
            <div className="planner-optimizer-explanation"><h3>Restricciones conflictivas</h3><ul>{Array.isArray(run.explanation.conflicts) && run.explanation.conflicts.length ? run.explanation.conflicts.map((item, index) => <li key={index}>{explanationText(item, "Restricción incompatible con el escenario actual")}</li>) : <li>El conjunto de restricciones duras no tiene solución compatible.</li>}</ul></div>
          ) : null}
          {run.status === "UNKNOWN" ? <Alert tone="info">No hay evidencia suficiente o el límite terminó sin una solución demostrable. Revisa los supuestos antes de usar esta ruta.</Alert> : null}
          {run.status === "OPTIMAL" || run.status === "FEASIBLE" ? (
            <div className="planner-optimizer-explanation">
              <h3>Comparación contra el escenario actual</h3>
              <div className="planner-optimizer-diff-grid"><div><strong>Añadidos</strong><ul>{added.length ? added.map((course) => <li key={course.course_code}>{course.course_code} · {course.term_code}</li>) : <li>Ninguno</li>}</ul></div><div><strong>Movidos</strong><ul>{moved.length ? moved.map((course) => <li key={course.course_code}>{course.course_code} · {current.get(course.course_code)} → {course.term_code}</li>) : <li>Ninguno</li>}</ul></div><div><strong>Retirados</strong><ul>{removed.length ? removed.map((course) => <li key={course.id}>{course.course_code} · {course.term_code}</li>) : <li>Ninguno</li>}</ul></div></div>
              <h3>Decisiones y supuestos</h3>
              <ul>{Array.isArray(run.explanation.explanations) && run.explanation.explanations.length ? run.explanation.explanations.map((item, index) => <li key={index}>{explanationText(item, "Decisión incluida en la ruta calculada")}</li>) : <li>La solución no reportó decisiones.</li>}</ul>
              {Array.isArray(run.explanation.assumptions) && run.explanation.assumptions.length ? <p className="muted-copy">Supuestos: {run.explanation.assumptions.map(assumptionLabel).join(" · ")}</p> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
