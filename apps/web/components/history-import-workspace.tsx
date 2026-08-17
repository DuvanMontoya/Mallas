"use client";

import { CheckCircle2, FileSearch, FileUp, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import {
  confirmHistoryImport,
  getHistoryImport,
  problemMessage,
  resolveHistoryImportCandidate,
  uploadHistoryImport,
  type HistoryImportCandidate,
  type HistoryImportPreview,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { EmptyState } from "./ui/empty-state";
import { StatusBadge } from "./ui/status-badge";

type CourseOption = { id: string; code: string; name: string };

function objectSummary(value: Record<string, unknown>) {
  return Object.entries(value)
    .filter(([, item]) => item !== null && item !== "")
    .slice(0, 8)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(" · ");
}

function candidateTone(candidate: HistoryImportCandidate) {
  if (candidate.decision !== "PENDING") return "passed" as const;
  if (candidate.status === "ERROR") return "blocked" as const;
  if (candidate.status === "CONFLICT") return "unknown" as const;
  return "in-progress" as const;
}

export function HistoryImportWorkspace({
  enrollmentId,
  initialPreview,
  courseOptions,
}: {
  enrollmentId: string;
  initialPreview: HistoryImportPreview | null;
  courseOptions: CourseOption[];
}) {
  const router = useRouter();
  const [preview, setPreview] = useState(initialPreview);
  const [file, setFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [decision, setDecision] = useState("ACCEPT");
  const [selectedCourseVersionId, setSelectedCourseVersionId] = useState("");
  const [externalCode, setExternalCode] = useState("");
  const [note, setNote] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selected = preview?.candidates.find((candidate) => candidate.id === selectedId) ?? null;
  const canConfirm = Boolean(preview && preview.unresolved_count === 0 && preview.error_count === 0 && preview.status !== "APPLIED");
  const progress = useMemo(() => {
    if (!preview?.candidate_count) return 0;
    return Math.round(((preview.candidate_count - preview.unresolved_count) / preview.candidate_count) * 100);
  }, [preview]);

  function editCandidate(candidate: HistoryImportCandidate) {
    setSelectedId(candidate.id);
    setDecision(candidate.decision === "PENDING" ? "ACCEPT" : candidate.decision);
    setSelectedCourseVersionId(candidate.selected_course_version_id ?? "");
    setExternalCode(candidate.external_code);
    setNote(candidate.note);
    setError(null);
    setMessage(null);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("El archivo supera el máximo de 10 MiB. Reduce su tamaño antes de crear el preview.");
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    const result = await uploadHistoryImport(enrollmentId, file, crypto.randomUUID());
    setPending(false);
    if (!result.data) {
      setError(problemMessage(result.failure?.problem ?? null, "No fue posible validar el archivo."));
      return;
    }
    setPreview(result.data);
    setMessage(result.data.created ? "Archivo validado. Revisa cada candidato antes de confirmar." : "Este archivo ya existía; se recuperó su preview sin duplicar registros.");
    router.replace(`/history/import?batch=${encodeURIComponent(result.data.id)}`);
  }

  async function resolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preview || !selected) return;
    setPending(true);
    setError(null);
    setMessage(null);
    const result = await resolveHistoryImportCandidate(
      preview.id,
      selected.id,
      {
        decision,
        selected_course_version_id: decision === "ACCEPT" || decision === "EXTERNAL" ? selectedCourseVersionId || null : null,
        external_code: decision === "EXTERNAL" ? externalCode.trim() : "",
        note: note.trim(),
      },
      { ifMatch: `"${selected.version}"` },
    );
    if (!result.data) {
      setPending(false);
      setError(problemMessage(result.failure?.problem ?? null, "No fue posible guardar la decisión."));
      return;
    }
    // Resolving a candidate advances the batch version. Reload the authoritative
    // preview so a subsequent confirmation never sends the pre-resolution token.
    const refreshed = await getHistoryImport(preview.id);
    setPending(false);
    if (!refreshed.data) {
      setError(problemMessage(refreshed.failure?.problem ?? null, "La decisión se guardó, pero no fue posible actualizar la versión del lote. Recarga antes de confirmar."));
      return;
    }
    setPreview(refreshed.data);
    setMessage("Decisión guardada con su versión y nota de reconciliación.");
    setSelectedId(null);
  }

  async function confirm() {
    if (!preview || !canConfirm) return;
    setPending(true);
    setError(null);
    setMessage(null);
    const result = await confirmHistoryImport(preview.id, { ifMatch: `"${preview.version}"` });
    setPending(false);
    if (!result.data) {
      setError(problemMessage(result.failure?.problem ?? null, "No fue posible confirmar la importación."));
      return;
    }
    setMessage(`Importación aplicada: ${result.data.created_attempts} intentos y ${result.data.created_recognitions} reconocimientos. La auditoría fue recalculada.`);
    setPreview({ ...preview, status: result.data.status, unresolved_count: 0 });
    router.refresh();
  }

  return (
    <div className="history-import-page">
      <Link className="governance-back-link" href="/history">← Volver a la historia</Link>
      <section className="panel history-import-hero">
        <div>
          <p className="eyebrow accent">Importación privada · preview obligatorio</p>
          <h1>Revisa los hechos antes de aplicarlos.</h1>
          <p>CSV, JSON y PDF se convierten en candidatos. Ninguna fila cambia tu historia hasta que resuelvas errores y confirmes explícitamente.</p>
        </div>
        <div className="history-import-safety"><ShieldCheck size={20} aria-hidden="true" /><strong>10 MiB máximo</strong><span>Sin ejecución, almacenamiento privado, fingerprint e idempotencia por matrícula.</span></div>
      </section>

      {error ? <Alert tone="error">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}

      {!preview ? (
        <section className="panel history-upload-panel" aria-labelledby="history-upload-title">
          <div className="section-heading"><div><p className="eyebrow">Paso 1</p><h2 id="history-upload-title">Selecciona una fuente</h2></div></div>
          <form className="history-upload-form" onSubmit={upload}>
            <label className="history-file-field">
              <FileUp size={24} aria-hidden="true" />
              <span><strong>{file?.name ?? "CSV, JSON o PDF"}</strong><small>{file ? `${Math.ceil(file.size / 1024)} KiB listos para validar` : "El archivo no se aplica automáticamente."}</small></span>
              <input type="file" accept=".csv,.json,.pdf,text/csv,application/json,application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
            </label>
            <button className="button button-primary" type="submit" disabled={!file || pending}>{pending ? "Validando…" : "Crear preview"}</button>
          </form>
        </section>
      ) : (
        <>
          <section className="history-import-progress panel" aria-label="Estado del lote">
            <div><span>Archivo</span><strong>{preview.original_filename}</strong></div>
            <div><span>Estado</span><strong>{preview.status}</strong></div>
            <div><span>Candidatos</span><strong>{preview.candidate_count}</strong></div>
            <div><span>Pendientes</span><strong>{preview.unresolved_count}</strong></div>
            <div><span>Errores</span><strong>{preview.error_count}</strong></div>
            <div className="history-progress-meter" role="progressbar" aria-label="Progreso de reconciliación" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span>Revisión {progress}%</span><div aria-hidden="true"><i style={{ width: `${progress}%` }} /></div></div>
          </section>

          {preview.validation_errors.length ? <Alert tone="error"><strong>El lote contiene errores de validación.</strong><pre>{JSON.stringify(preview.validation_errors, null, 2)}</pre></Alert> : null}

          <section className="history-import-layout">
            <div className="panel history-candidates">
              <div className="section-heading"><div><p className="eyebrow">Paso 2</p><h2>Candidatos extraídos</h2></div><span className="tag tag-outline">{preview.parser_version}</span></div>
              {preview.candidates.length ? <ol className="history-candidate-list">{preview.candidates.map((candidate) => (
                <li key={candidate.id}>
                  <button type="button" className={selectedId === candidate.id ? "selected" : undefined} aria-pressed={selectedId === candidate.id} aria-controls="history-reconciliation-panel" onClick={() => editCandidate(candidate)}>
                    <span className="history-candidate-number">{candidate.row_number}</span>
                    <span><strong>{String(candidate.normalized_payload.course_code ?? candidate.raw_payload.course_code ?? "Registro sin código")}</strong><small>{objectSummary(candidate.normalized_payload)}</small><small>{candidate.source_locator} · confianza {candidate.confidence}%</small></span>
                    <StatusBadge tone={candidateTone(candidate)} label={candidate.decision === "PENDING" ? candidate.status : candidate.decision} />
                  </button>
                </li>
              ))}</ol> : <EmptyState title="El archivo no produjo candidatos" description="Comprueba que el formato contenga registros y usa una plantilla compatible." />}
            </div>

            <aside className="panel history-reconciliation" id="history-reconciliation-panel" aria-labelledby="history-reconciliation-title">
              <div className="section-heading"><div><p className="eyebrow">Reconciliación</p><h2 id="history-reconciliation-title">{selected ? `Fila ${selected.row_number}` : "Selecciona una fila"}</h2></div></div>
              {!selected ? <EmptyState title="Nada seleccionado" description="Abre un candidato para aceptar, reconocer como externo o excluirlo con una decisión auditable." /> : (
                <form className="history-form" onSubmit={resolve}>
                  {selected.parse_errors.length ? <Alert tone="error"><pre>{JSON.stringify(selected.parse_errors, null, 2)}</pre></Alert> : null}
                  {selected.conflict_details.length ? <Alert tone="info"><pre>{JSON.stringify(selected.conflict_details, null, 2)}</pre></Alert> : null}
                  <label className="field-group"><span>Decisión</span><select value={decision} onChange={(event) => setDecision(event.target.value)}><option value="ACCEPT">Aceptar como intento</option><option value="EXTERNAL">Registrar reconocimiento externo</option><option value="SKIP">No aplicar</option></select></label>
                  {decision === "ACCEPT" || decision === "EXTERNAL" ? <>
                    <label className="field-group"><span>{decision === "EXTERNAL" ? "Asignatura destino" : "Asignatura del plan"}</span><select value={selectedCourseVersionId} onChange={(event) => setSelectedCourseVersionId(event.target.value)} required={decision === "EXTERNAL"}><option value="">Usar coincidencia sugerida</option>{courseOptions.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.name}</option>)}</select></label>
                  </> : null}
                  {decision === "EXTERNAL" ? <>
                    <label className="field-group"><span>Código externo</span><input value={externalCode} onChange={(event) => setExternalCode(event.target.value)} required /></label>
                  </> : null}
                  <label className="field-group"><span>Nota de decisión</span><textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} required={decision !== "ACCEPT" || selected.status === "CONFLICT"} /></label>
                  <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Guardando…" : "Guardar decisión"}</button>
                </form>
              )}
            </aside>
          </section>

          <section className="panel history-confirm-panel">
            <div><FileSearch size={20} aria-hidden="true" /><span><strong>Paso 3 · aplicar lote</strong><small>{canConfirm ? "Todos los candidatos están resueltos y el lote puede aplicarse." : "Resuelve pendientes y errores antes de confirmar."}</small></span></div>
            {preview.status === "APPLIED" ? <StatusBadge tone="passed" label="Importación aplicada" /> : <button className="button button-primary" type="button" onClick={() => void confirm()} disabled={!canConfirm || pending}><CheckCircle2 size={16} aria-hidden="true" /> Confirmar e importar</button>}
          </section>
        </>
      )}
    </div>
  );
}
