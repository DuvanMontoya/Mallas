"use client";

import { FileUp, History, PencilLine, Plus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import {
  annulHistoryAttempt,
  createHistoryAttempt,
  problemMessage,
  updateHistoryAttempt,
  type HistoryAttempt,
  type HistoryAttemptPage,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { EmptyState } from "./ui/empty-state";
import { StatusBadge, type StatusTone } from "./ui/status-badge";

const ATTEMPT_STATUSES = [
  "PASSED",
  "ENROLLED",
  "FAILED",
  "VALIDATED",
  "HOMOLOGATED",
  "TRANSFERRED",
  "WITHDRAWN",
  "CANCELLED",
] as const;

function statusLabel(status: string) {
  return {
    PASSED: "Aprobado",
    ENROLLED: "En curso",
    FAILED: "No aprobado",
    VALIDATED: "Validado",
    HOMOLOGATED: "Homologado",
    TRANSFERRED: "Transferido",
    WITHDRAWN: "Retirado",
    CANCELLED: "Cancelado",
    ANNULLED: "Anulado",
    PLANNED: "Planeado",
  }[status] ?? status;
}

function originLabel(origin: string) {
  return {
    IMPORT: "Importación",
    MANUAL: "Registro manual",
  SIA: "Sistema institucional",
  }[origin] ?? "Origen registrado";
}

function statusTone(status: string): StatusTone {
  if (["PASSED", "VALIDATED", "HOMOLOGATED", "TRANSFERRED"].includes(status)) return "passed";
  if (status === "ENROLLED") return "in-progress";
  if (["FAILED", "WITHDRAWN", "CANCELLED"].includes(status)) return "blocked";
  if (status === "ANNULLED") return "unknown";
  return "neutral";
}

function quoted(version: string) {
  return `"${version}"`;
}

export function HistoryWorkspace({
  enrollmentId,
  studentName,
  attemptsPage,
  courseOptions = [],
  termOptions = [],
  reviewPending = false,
}: {
  enrollmentId: string;
  studentName: string;
  attemptsPage: HistoryAttemptPage;
  courseOptions?: Array<{ code: string; name: string }>;
  termOptions?: string[];
  reviewPending?: boolean;
}) {
  const router = useRouter();
  const [attempts, setAttempts] = useState(attemptsPage.items);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [courseCode, setCourseCode] = useState("");
  const [termCode, setTermCode] = useState("");
  const [attemptNumber, setAttemptNumber] = useState("1");
  const [status, setStatus] = useState("PASSED");
  const [grade, setGrade] = useState("");
  const [credits, setCredits] = useState("");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const selected = attempts.find((attempt) => attempt.id === selectedId) ?? null;
  const summary = useMemo(() => ({
    total: attempts.filter((attempt) => attempt.status !== "ANNULLED").length,
    passed: attempts.filter((attempt) => ["PASSED", "VALIDATED", "HOMOLOGATED", "TRANSFERRED"].includes(attempt.status)).length,
    inProgress: attempts.filter((attempt) => attempt.status === "ENROLLED").length,
    credits: attempts.reduce((sum, attempt) => sum + (attempt.status === "ANNULLED" ? 0 : attempt.credits_earned), 0),
  }), [attempts]);

  function startEdit(attempt: HistoryAttempt) {
    setSelectedId(attempt.id);
    setStatus(attempt.status);
    setGrade(attempt.grade ?? "");
    setCredits(String(attempt.credits_earned));
    setNotes(attempt.notes);
    setError(null);
    setMessage(null);
  }

  function resetForm() {
    setSelectedId(null);
    setCourseCode("");
    setTermCode("");
    setAttemptNumber("1");
    setStatus("PASSED");
    setGrade("");
    setCredits("");
    setNotes("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected && courseOptions.length && !courseOptions.some((course) => course.code === courseCode.trim())) {
      setError("Selecciona una asignatura válida del plan antes de guardar el intento.");
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    const numericCredits = credits.trim() ? Number(credits) : null;
    const numericGrade = grade.trim() ? grade.trim() : null;
    const result = selected
      ? await updateHistoryAttempt(
          selected.id,
          {
            status,
            grade: numericGrade,
            credits_earned: numericCredits,
            notes,
          },
          { ifMatch: quoted(selected.version) },
        )
      : await createHistoryAttempt({
          enrollment_id: enrollmentId,
          course_code: courseCode.trim(),
          term_code: termCode.trim(),
          attempt_number: Number(attemptNumber),
          status,
          grade: numericGrade,
          credits_earned: numericCredits,
          notes,
        });
    setPending(false);
    if (!result.data) {
      setError(problemMessage(result.failure?.problem ?? null, "No fue posible guardar el intento académico."));
      return;
    }
    const savedAttempt = result.data;
    setAttempts((current) => selected
      ? current.map((attempt) => attempt.id === savedAttempt.id ? savedAttempt : attempt)
      : [...current, savedAttempt]);
    setMessage(reviewPending ? "El intento quedó guardado. Los cálculos se reanudarán cuando administración confirme la revisión curricular." : selected ? "El intento se actualizó y la auditoría fue recalculada." : "El intento se agregó y la auditoría fue recalculada.");
    resetForm();
    router.refresh();
  }

  async function annul(attempt: HistoryAttempt) {
    setPending(true);
    setError(null);
    setMessage(null);
    const result = await annulHistoryAttempt(attempt.id, { ifMatch: quoted(attempt.version) });
    setPending(false);
    if (!result.data) {
      setError(problemMessage(result.failure?.problem ?? null, "No fue posible anular el intento."));
      return;
    }
    const annulledAttempt = result.data;
    setAttempts((current) => current.map((item) => item.id === annulledAttempt.id ? annulledAttempt : item));
    setMessage("El intento quedó anulado de forma auditable; no se eliminó la evidencia histórica.");
    resetForm();
    router.refresh();
  }

  return (
    <div className="history-page">
      <section className="history-decision-hero">
        <div>
          <p className="eyebrow accent">Registro privado</p>
          <h1>Historia académica</h1>
          <span>{summary.passed} aprobadas · {summary.inProgress} en curso · {summary.credits} créditos reportados</span>
        </div>
        <div className="history-hero-actions">
          <Link className="button button-primary" href="/history/import"><FileUp size={16} aria-hidden="true" /> Importar archivo</Link>
          <a className="button button-secondary" href="#history-editor-title"><Plus size={16} aria-hidden="true" /> Añadir manualmente</a>
          <span>{studentName} · información privada</span>
        </div>
      </section>
      {reviewPending ? <Alert tone="warning">Puedes conservar y corregir tu historia. Los cálculos de avance y elegibilidad están pausados hasta que administración confirme la revisión curricular aplicable.</Alert> : null}

      {error ? <Alert tone="error">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}

      <section className="history-layout">
        <div className="panel history-ledger">
          <div className="section-heading">
            <div><p className="eyebrow">Tu registro</p><h2>Asignaturas e intentos</h2></div>
            <span className="tag tag-outline">{attempts.length} registros</span>
          </div>
          {attempts.length ? (
            <div className="table-scroll">
              <table className="history-table">
                <caption>Historia de {studentName}; los registros anulados se conservan.</caption>
                <thead><tr><th scope="col">Asignatura</th><th scope="col">Período</th><th scope="col">Estado</th><th scope="col">Nota</th><th scope="col">Créditos</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
                <tbody>{attempts.map((attempt) => (
                  <tr key={attempt.id} className={attempt.status === "ANNULLED" ? "history-row-annulled" : undefined}>
                    <th scope="row"><strong>{attempt.course_code}</strong><span>{attempt.course_name}</span><small>Intento {attempt.attempt_number} · {originLabel(attempt.origin)}</small></th>
                    <td>{attempt.term_code}</td>
                    <td><StatusBadge tone={statusTone(attempt.status)} label={statusLabel(attempt.status)} /></td>
                    <td>{attempt.grade ?? "—"}</td>
                    <td>{attempt.credits_earned}</td>
                    <td><button className="icon-button" type="button" onClick={() => startEdit(attempt)} disabled={pending || attempt.status === "ANNULLED"} aria-label={`Editar ${attempt.course_code}`}><PencilLine size={15} aria-hidden="true" /></button></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          ) : <EmptyState title="Aún no hay intentos" description="Agrega un registro manual o importa una historia para iniciar una auditoría con hechos verificables." />}
        </div>

        <aside className="panel history-editor" aria-labelledby="history-editor-title">
          <div className="section-heading">
            <div><p className="eyebrow">{selected ? "Corrección trazable" : "Entrada manual"}</p><h2 id="history-editor-title">{selected ? `Editar ${selected.course_code}` : "Agregar un intento"}</h2></div>
            {selected ? <button className="icon-button" type="button" onClick={resetForm} aria-label="Cancelar edición"><RotateCcw size={16} aria-hidden="true" /></button> : null}
          </div>
          <p className="muted-copy">{selected ? "Sólo se cambian campos permitidos; el intento original permanece en la auditoría." : "Selecciona datos del plan cuando estén disponibles. Los duplicados no se sobrescriben."}</p>
          <form className="history-form" onSubmit={submit}>
            {!selected ? <>
              <label className="field-group"><span>Asignatura del plan</span><input list="history-course-options" value={courseCode} onChange={(event) => setCourseCode(event.target.value)} placeholder="Busca por código" autoComplete="off" required /></label>
              <datalist id="history-course-options">{courseOptions.map((course) => <option key={course.code} value={course.code}>{course.name}</option>)}</datalist>
              <label className="field-group"><span>Período académico</span>{termOptions.length ? <select value={termCode} onChange={(event) => setTermCode(event.target.value)} required><option value="">Selecciona un período</option>{termOptions.map((term) => <option key={term} value={term}>{term}</option>)}</select> : <input value={termCode} onChange={(event) => setTermCode(event.target.value)} placeholder="Ej. 2026-2S" required />}</label>
              <label className="field-group"><span>Número de intento</span><input type="number" min="1" max="99" value={attemptNumber} onChange={(event) => setAttemptNumber(event.target.value)} required /></label>
            </> : null}
            <label className="field-group"><span>Estado oficial</span><select value={status} onChange={(event) => setStatus(event.target.value)}>{ATTEMPT_STATUSES.map((item) => <option key={item} value={item}>{statusLabel(item)}</option>)}</select></label>
            <div className="history-form-row">
              <label className="field-group"><span>Nota</span><input inputMode="decimal" value={grade} onChange={(event) => setGrade(event.target.value)} placeholder="0.00 – 5.00" /></label>
              <label className="field-group"><span>Créditos obtenidos</span><input type="number" min="0" max="99" value={credits} onChange={(event) => setCredits(event.target.value)} /></label>
            </div>
            <label className="field-group"><span>Nota de trazabilidad</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label>
            <button className="button button-primary" type="submit" disabled={pending || (!selected && (!courseCode.trim() || !termCode.trim()))}><Plus size={16} aria-hidden="true" /> {pending ? "Guardando…" : selected ? "Guardar corrección" : "Agregar intento"}</button>
          </form>
          {selected && selected.status !== "ANNULLED" ? <div className="history-annul"><History size={16} aria-hidden="true" /><div><strong>Anulación auditable</strong><p>No borra el registro ni su procedencia.</p></div><button className="button button-secondary" type="button" onClick={() => void annul(selected)} disabled={pending}>Anular intento</button></div> : null}
        </aside>
      </section>
    </div>
  );
}
