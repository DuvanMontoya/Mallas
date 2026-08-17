"use client";

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { GripVertical, Lock, LockOpen, Plus, Share2, Trash2, WandSparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import {
  addPlannedCourse,
  archiveScenario,
  createScenario,
  deletePlannedCourse,
  duplicateScenario,
  getScenarioCompare,
  type AcademicTerm,
  type ApiComponents,
  type PlanningScenario,
  type ScenarioCompare,
  updatePlannedCourse,
  updateScenario,
} from "@/lib/api";

import { Alert } from "./ui/alert";
import { OptimizerPanel } from "./optimizer-panel";
import { PlannerTermColumn, ScenarioCompare as ScenarioCompareLayout } from "./ui/foundation";
import { StatusBadge, type StatusTone } from "./ui/status-badge";

type CurriculumCourse = ApiComponents["schemas"]["MapCourseView"];
type PlannerTerm = Pick<AcademicTerm, "id" | "code">;

function toneForState(value: string): StatusTone {
  if (["SATISFIED", "VALID", "OFFERED"].includes(value)) return "eligible";
  if (["UNSATISFIED", "WARNINGS", "NOT_OFFERED"].includes(value)) return "blocked";
  if (value === "UNKNOWN") return "unknown";
  return "neutral";
}

function quoteVersion(version: number) {
  return `"${version}"`;
}

function warningLabel(code: string) {
  return code
    .toLocaleLowerCase("es-CO")
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toLocaleUpperCase("es-CO"));
}

function PlannerCourseCard({
  course,
  terms,
  pending,
  onMove,
  onToggleLock,
  onDelete,
}: {
  course: PlanningScenario["planned_courses"][number];
  terms: PlannerTerm[];
  pending: boolean;
  onMove: (termId: string) => void;
  onToggleLock: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: course.id,
    disabled: pending || course.is_locked,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 2 }
    : undefined;
  return (
    <article
      ref={setNodeRef}
      className={`planner-course-card${isDragging ? " planner-course-dragging" : ""}`}
      style={style}
      data-course-code={course.course_code}
    >
      <div className="planner-course-heading">
        <span className="course-code-label">{course.course_code}</span>
        <span className="tag tag-outline">{course.credits ?? "—"} cr.</span>
      </div>
      <h4>{course.course_name}</h4>
      <p>{course.section_group_code ? `Grupo ${course.section_group_code}` : "Grupo por seleccionar"}</p>
      <div className="planner-course-actions">
        <button
          className="planner-drag-handle"
          type="button"
          {...attributes}
          {...listeners}
          disabled={pending || course.is_locked}
          aria-label={course.is_locked ? `${course.course_code} está bloqueado` : `Arrastrar ${course.course_code}`}
          title={course.is_locked ? "Desbloquea para mover" : "Arrastra para mover"}
        >
          <GripVertical size={16} aria-hidden="true" />
          <span className="sr-only">Arrastrar</span>
        </button>
        <label className="planner-move-select">
          <span>Mover a</span>
          <select
            value={course.term_id}
            onChange={(event) => onMove(event.target.value)}
            disabled={pending || course.is_locked}
            aria-label={`Mover ${course.course_code} a otro período`}
          >
            {terms.map((term) => <option key={term.id} value={term.id}>{term.code}</option>)}
          </select>
        </label>
        <button
          className="icon-button planner-action-button"
          type="button"
          onClick={onToggleLock}
          disabled={pending}
          aria-label={course.is_locked ? `Desbloquear ${course.course_code}` : `Bloquear ${course.course_code}`}
          title={course.is_locked ? "Desbloquear" : "Bloquear elección"}
        >
          {course.is_locked ? <Lock size={15} aria-hidden="true" /> : <LockOpen size={15} aria-hidden="true" />}
        </button>
        <button
          className="icon-button planner-action-button planner-delete-button"
          type="button"
          onClick={onDelete}
          disabled={pending || course.is_locked}
          aria-label={`Quitar ${course.course_code} del escenario`}
          title={course.is_locked ? "Desbloquea para quitar" : "Quitar del escenario"}
        >
          <Trash2 size={15} aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

function TermDropColumn({
  term,
  terms,
  courses,
  pending,
  onMove,
  onToggleLock,
  onDelete,
}: {
  term: PlannerTerm;
  terms: PlannerTerm[];
  courses: PlanningScenario["planned_courses"];
  pending: boolean;
  onMove: (courseId: string, termId: string) => void;
  onToggleLock: (course: PlanningScenario["planned_courses"][number]) => void;
  onDelete: (course: PlanningScenario["planned_courses"][number]) => void;
}) {
  const { isOver, setNodeRef } = useDroppable({ id: `term:${term.id}`, data: { termId: term.id } });
  return (
    <div ref={setNodeRef} className={`planner-drop-column${isOver ? " planner-drop-over" : ""}`} aria-label={`Período ${term.code}; ${courses.length} cursos. Usa el selector Mover a para cambiar cursos sin arrastrar.`}>
      <PlannerTermColumn title={term.code} subtitle={`${courses.length} curso${courses.length === 1 ? "" : "s"}`}>
        {courses.length ? courses.map((course) => (
          <PlannerCourseCard
            key={course.id}
            course={course}
            terms={terms}
            pending={pending}
            onMove={(termId) => onMove(course.id, termId)}
            onToggleLock={() => onToggleLock(course)}
            onDelete={() => onDelete(course)}
          />
        )) : <p className="planner-column-empty">Suelta aquí un curso para proyectarlo en este período.</p>}
      </PlannerTermColumn>
    </div>
  );
}

export function PlannerBoard({
  initialScenarios,
  initialSelectedId,
  initialCompare,
  terms,
  courseOptions,
  failureMessage,
}: {
  initialScenarios: PlanningScenario[];
  initialSelectedId?: string;
  initialCompare: ScenarioCompare | null;
  terms: PlannerTerm[];
  courseOptions: CurriculumCourse[];
  failureMessage?: string;
}) {
  const router = useRouter();
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor));
  const [scenarios, setScenarios] = useState(initialScenarios);
  const [selectedId, setSelectedId] = useState(initialSelectedId ?? initialScenarios[0]?.id ?? "");
  const [compare, setCompare] = useState<ScenarioCompare | null>(initialCompare);
  const [compareId, setCompareId] = useState(initialCompare?.right.id ?? "");
  const [newName, setNewName] = useState("");
  const [selectedCourseId, setSelectedCourseId] = useState(courseOptions[0]?.id ?? "");
  const [selectedTermId, setSelectedTermId] = useState(terms[0]?.id ?? "");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const scenario = scenarios.find((item) => item.id === selectedId) ?? scenarios[0] ?? null;
  const planningTerms = useMemo(() => {
    const seen = new Set<string>();
    return terms.filter((term) => {
      if (seen.has(term.id)) return false;
      seen.add(term.id);
      return true;
    });
  }, [terms]);
  const scenarioTerms = useMemo(() => {
    if (!scenario) return planningTerms;
    const known = new Map(planningTerms.map((term) => [term.id, term]));
    for (const course of scenario.planned_courses) {
      if (!known.has(course.term_id)) known.set(course.term_id, { id: course.term_id, code: course.term_code });
    }
    return [...known.values()];
  }, [planningTerms, scenario]);

  function applyScenario(next: PlanningScenario) {
    setScenarios((current) => current.some((item) => item.id === next.id)
      ? current.map((item) => item.id === next.id ? next : item)
      : [...current, next]);
    setSelectedId(next.id);
  }

  async function runMutation<T extends { data: PlanningScenario | null; failure: { problem: { detail?: string } | null } | null }>(request: () => Promise<T>) {
    setPending(true);
    setMessage(null);
    const result = await request();
    setPending(false);
    if (result.failure || !result.data) {
      setMessage(result.failure?.problem?.detail ?? "No se pudo actualizar el escenario.");
      return null;
    }
    applyScenario(result.data);
    return result.data;
  }

  async function moveCourse(courseId: string, termId: string) {
    if (!scenario || termId === scenario.planned_courses.find((item) => item.id === courseId)?.term_id) return;
    await runMutation(() => updatePlannedCourse(scenario.id, courseId, { term_id: termId }, { ifMatch: quoteVersion(scenario.version) }));
  }

  function handleDragEnd(event: DragEndEvent) {
    const overId = event.over?.id;
    if (!scenario || typeof overId !== "string" || !overId.startsWith("term:")) return;
    void moveCourse(String(event.active.id), overId.slice("term:".length));
  }

  async function toggleLock(course: PlanningScenario["planned_courses"][number]) {
    if (!scenario) return;
    await runMutation(() => updatePlannedCourse(
      scenario.id,
      course.id,
      { is_locked: !course.is_locked },
      { ifMatch: quoteVersion(scenario.version) },
    ));
  }

  async function removeCourse(course: PlanningScenario["planned_courses"][number]) {
    if (!scenario) return;
    await runMutation(() => deletePlannedCourse(scenario.id, course.id, { ifMatch: quoteVersion(scenario.version) }));
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) return;
    const created = await runMutation(() => createScenario({
      name,
      target_term_id: selectedTermId || null,
    }));
    if (created) setNewName("");
  }

  async function handleAddCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!scenario || !selectedCourseId || !selectedTermId) return;
    await runMutation(() => addPlannedCourse(
      scenario.id,
      { course_version_id: selectedCourseId, term_id: selectedTermId, priority: 0, notes: "" },
      { ifMatch: quoteVersion(scenario.version) },
    ));
  }

  async function handleDuplicate() {
    if (!scenario) return;
    await runMutation(() => duplicateScenario(scenario.id, `${scenario.name} — copia`));
  }

  async function handleArchive() {
    if (!scenario) return;
    await runMutation(() => archiveScenario(scenario.id, { ifMatch: quoteVersion(scenario.version) }));
  }

  async function handleShare() {
    if (!scenario) return;
    const updated = await runMutation(() => updateScenario(
      scenario.id,
      { sharing_enabled: !scenario.sharing_enabled },
      { ifMatch: quoteVersion(scenario.version) },
    ));
    if (updated?.sharing_enabled && updated.share_token) {
      setMessage(`Enlace privado listo: ${window.location.origin}/shared/scenarios/${updated.share_token}`);
    }
  }

  async function handleCompare(nextId: string) {
    setCompareId(nextId);
    if (!scenario || !nextId) {
      setCompare(null);
      return;
    }
    const result = await getScenarioCompare({ leftId: scenario.id, rightId: nextId });
    setCompare(result.data);
    if (result.failure) setMessage(result.failure.problem?.detail ?? "No se pudo comparar los escenarios.");
  }

  function selectScenario(nextId: string) {
    setSelectedId(nextId);
    setCompare(null);
    setCompareId("");
    router.replace(`/planner?scenario=${encodeURIComponent(nextId)}`);
  }

  if (!scenario) {
    return (
      <div className="planner-page">
        <section className="panel planner-hero">
          <div><p className="eyebrow accent">Planificador · escenarios privados</p><h1>Planea sin alterar tu historia real.</h1><p>Un escenario proyecta decisiones futuras, conserva tus hechos académicos separados y deja cada advertencia visible.</p></div>
        </section>
        <section className="panel planner-empty-panel">
          <h2>Comienza un escenario</h2>
          <p>No hay escenarios disponibles para tu matrícula. Crea uno para organizar períodos, cursos y preferencias.</p>
          <form className="planner-create-form" onSubmit={handleCreate}>
            <label className="field-group"><span>Nombre del escenario</span><input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Ruta de grado" /></label>
            <button className="button button-primary" type="submit" disabled={pending || !newName.trim()}><Plus size={16} aria-hidden="true" /> Crear escenario</button>
          </form>
          {failureMessage ? <Alert tone="error">{failureMessage}</Alert> : null}
        </section>
      </div>
    );
  }

  const warnings = scenario.validation.warnings;
  const courseByTerm = (termId: string) => scenario.planned_courses.filter((course) => course.term_id === termId);
  const otherScenarios = scenarios.filter((item) => item.id !== scenario.id && item.status === "ACTIVE");
  const auditPayload = scenario.audit_projection?.payload ?? {};
  const projectedStatus = typeof auditPayload.status === "string" ? auditPayload.status : scenario.audit_projection?.unknown_count ? "UNKNOWN" : "READY";

  return (
    <div className="planner-page">
      <section className="panel planner-hero">
        <div>
          <p className="eyebrow accent">Planificador · escenario privado</p>
          <h1>Planea sin alterar tu historia real.</h1>
          <p>Arrastra cursos entre períodos o usa los controles de teclado. Las reglas se verifican en el backend; un escenario nunca crea ni edita intentos académicos oficiales.</p>
        </div>
        <div className="planner-privacy-card"><Lock size={18} aria-hidden="true" /><strong>Privado por defecto</strong><span>Compartir sólo publica una vista mínima sin estudiante, matrícula, historial ni auditoría personal.</span></div>
      </section>

      <section className="panel planner-toolbar" aria-labelledby="planner-controls-title">
        <div className="section-heading"><div><p className="eyebrow">Control de escenario</p><h2 id="planner-controls-title">Tu ruta de planificación</h2></div><StatusBadge tone={toneForState(scenario.validation.state)} label={scenario.validation.state === "VALID" ? "Sin advertencias" : "Requiere revisión"} /></div>
        <div className="planner-toolbar-grid">
          <label className="field-group"><span>Escenario activo</span><select value={scenario.id} onChange={(event) => selectScenario(event.target.value)}><option value={scenario.id}>{scenario.name}</option>{otherScenarios.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div className="planner-toolbar-actions"><button className="button button-secondary" type="button" onClick={handleDuplicate} disabled={pending}><WandSparkles size={15} aria-hidden="true" /> Duplicar</button><button className="button button-secondary" type="button" onClick={handleShare} disabled={pending}><Share2 size={15} aria-hidden="true" /> {scenario.sharing_enabled ? "Dejar de compartir" : "Compartir vista"}</button><button className="button button-quiet" type="button" onClick={handleArchive} disabled={pending}>Archivar</button></div>
        </div>
        {scenario.sharing_enabled && scenario.share_token ? <p className="planner-share-note" role="status">Vista compartible activa. El enlace no contiene datos personales: <code>{scenario.share_token}</code></p> : null}
        <form className="planner-create-form planner-create-inline" onSubmit={handleCreate}><label className="field-group"><span>Nuevo escenario</span><input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Ej. Ruta con práctica" /></label><button className="button button-primary" type="submit" disabled={pending || !newName.trim()}><Plus size={15} aria-hidden="true" /> Crear</button></form>
      </section>

      {message ? <Alert tone="error">{message}</Alert> : null}
      {failureMessage ? <Alert tone="error">{failureMessage}</Alert> : null}

      <section className="planner-section" aria-labelledby="planner-board-title">
        <div className="section-heading"><div><p className="eyebrow">Malla personal</p><h2 id="planner-board-title">Ordena tus próximos períodos</h2></div><span className="tag tag-outline">Versión {scenario.version}</span></div>
        <p className="planner-instruction" id="planner-board-instruction">Arrastra una tarjeta a otra columna. Si no puedes arrastrar, usa el selector «Mover a» de cada tarjeta.</p>
        <DndContext sensors={sensors} onDragEnd={handleDragEnd} accessibility={{ screenReaderInstructions: { draggable: "Para mover este curso, usa las flechas del teclado o el selector Mover a." } }}>
          <div className="planner-term-grid" aria-describedby="planner-board-instruction">
            {scenarioTerms.map((term) => <TermDropColumn key={term.id} term={term} terms={scenarioTerms} courses={courseByTerm(term.id)} pending={pending} onMove={moveCourse} onToggleLock={toggleLock} onDelete={removeCourse} />)}
          </div>
        </DndContext>
      </section>

      <section className="panel planner-add-panel" aria-labelledby="planner-add-title">
        <div className="section-heading"><div><p className="eyebrow">Añadir al escenario</p><h2 id="planner-add-title">Proyecta una asignatura</h2></div></div>
        {courseOptions.length && scenarioTerms.length ? <form className="planner-add-form" onSubmit={handleAddCourse}><label className="field-group"><span>Asignatura</span><select value={selectedCourseId} onChange={(event) => setSelectedCourseId(event.target.value)}>{courseOptions.map((course) => <option key={course.id} value={course.id}>{course.code} · {course.name}</option>)}</select></label><label className="field-group"><span>Período</span><select value={selectedTermId} onChange={(event) => setSelectedTermId(event.target.value)}>{scenarioTerms.map((term) => <option key={term.id} value={term.id}>{term.code}</option>)}</select></label><button className="button button-primary" type="submit" disabled={pending}><Plus size={15} aria-hidden="true" /> Añadir</button></form> : <p className="muted-copy">No hay cursos o períodos verificables disponibles para añadir. Consulta la malla y la oferta antes de completar este escenario.</p>}
      </section>

      <div className="planner-support-grid">
        <section className="panel planner-validation-panel" aria-labelledby="planner-validation-title"><div className="section-heading"><div><p className="eyebrow">Explicabilidad</p><h2 id="planner-validation-title">Advertencias de la ruta</h2></div><span className="tag tag-outline">{warnings.length} señal{warnings.length === 1 ? "" : "es"}</span></div>{warnings.length ? <ul className="planner-warning-list">{warnings.map((warning, index) => <li key={`${warning.code}-${warning.course_code ?? "scenario"}-${index}`}><StatusBadge tone={warning.severity === "ERROR" ? "blocked" : "unknown"} label={warningLabel(warning.code)} /><span>{warning.detail}</span></li>)}</ul> : <p className="muted-copy">No hay advertencias para los cursos actuales; la ausencia de advertencias no reemplaza la fuente normativa.</p>}</section>
        <section className="panel planner-audit-panel" aria-labelledby="planner-audit-title"><div className="section-heading"><div><p className="eyebrow">Motor determinista</p><h2 id="planner-audit-title">Auditoría proyectada</h2></div><StatusBadge tone={toneForState(projectedStatus)} label={projectedStatus} /></div><p>{scenario.audit_projection?.unknown_count ? "La revisión no permite calcular una auditoría completa; el resultado queda por verificar." : "La proyección usa una copia inmutable de tu historia y los cursos del escenario."}</p><dl className="planner-audit-facts"><div><dt>Cursos proyectados</dt><dd>{scenario.planned_courses.length}</dd></div><div><dt>Versión del motor</dt><dd>{scenario.audit_projection?.engine_version ?? "—"}</dd></div><div><dt>Huella de resultado</dt><dd><code>{scenario.audit_projection?.result_hash.slice(0, 12) ?? "—"}</code></dd></div></dl></section>
      </div>

      <OptimizerPanel scenario={scenario} />

      <section className="panel planner-compare-panel" aria-labelledby="planner-compare-title"><div className="section-heading"><div><p className="eyebrow">Decisión</p><h2 id="planner-compare-title">Compara dos rutas</h2></div></div><div className="planner-compare-toolbar"><label className="field-group"><span>Comparar con</span><select value={compareId} onChange={(event) => void handleCompare(event.target.value)}><option value="">Selecciona un escenario</option>{otherScenarios.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>{compare ? <ScenarioCompareLayout leftLabel={compare.left.name} rightLabel={compare.right.name} left={<CompareList title="Se mantienen" items={compare.unchanged.map((code) => `${code} · sin cambio`)} />} right={<div className="planner-compare-detail"><CompareList title="Añadidos" items={compare.added.map((item) => `${item.course_code} · ${item.term_code ?? "período por verificar"}`)} /><CompareList title="Movidos" items={compare.moved.map((item) => `${item.course_code} · ${item.from_term} → ${item.to_term}`)} /><CompareList title="Retirados" items={compare.removed.map((item) => `${item.course_code} · ${item.term_code ?? "período por verificar"}`)} /></div>} /> : <p className="muted-copy">Elige otra ruta para ver cursos añadidos, retirados, movidos y sin cambio.</p>}</section>
    </div>
  );
}

function CompareList({ title, items }: { title: string; items: string[] }) {
  return <section className="planner-compare-list"><h3>{title}</h3>{items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted-copy">Ninguno</p>}</section>;
}
