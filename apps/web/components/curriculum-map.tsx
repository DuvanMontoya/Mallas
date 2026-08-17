"use client";

import { ArrowDown, ArrowRight, ArrowUp, ChevronRight, Printer, RotateCcw, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import type { CurriculumMap } from "@/lib/api";

import {
  Alert,
  Button,
  CourseCard,
  CourseStatusBadge,
  CurriculumGrid,
  EmptyState,
  EvidencePopover,
  RequirementChip,
  StatusBadge,
  UnknownState,
} from "./ui";
import type { StatusTone } from "./ui/status-badge";

type MapCourse = CurriculumMap["courses"][number];
type MapGroup = CurriculumMap["groups"][number];
type MapComponent = CurriculumMap["components"][number];
type MapRequirement = MapCourse["requirements"][number];
type LayoutId = CurriculumMap["layout_policy"]["available_layouts"][number]["id"];

type MapPreferences = {
  layout: LayoutId | string;
  query: string;
  component: string;
  group: string;
  status: string;
  credits: string;
  offering: string;
  selected: string | null;
};

const statusLabels: Record<string, string> = {
  PASSED: "Aprobado",
  IN_PROGRESS: "En curso",
  ELIGIBLE: "Puedes cursarlo",
  BLOCKED: "Bloqueado",
  UNKNOWN: "Por verificar",
  NOT_ASSESSED: "Sin estado personal",
};

const offeringLabels: Record<string, string> = {
  AVAILABLE: "Con oferta registrada",
  NOT_AVAILABLE: "Oferta cancelada",
  NOT_REPORTED: "Sin oferta registrada",
  UNKNOWN: "Oferta por seleccionar",
};

function statusLabel(value: string) {
  return statusLabels[value] ?? value.replaceAll("_", " ");
}

function toneFor(value: string): StatusTone {
  if (value === "PASSED") return "passed";
  if (value === "IN_PROGRESS") return "in-progress";
  if (value === "ELIGIBLE" || value === "AVAILABLE") return "eligible";
  if (value === "BLOCKED" || value === "NOT_AVAILABLE") return "blocked";
  if (["UNKNOWN", "NOT_REPORTED"].includes(value)) return "unknown";
  return "neutral";
}

function readMapPreferences(params: URLSearchParams, defaultLayout: string): MapPreferences {
  return {
    layout: params.get("layout") ?? defaultLayout,
    query: params.get("q") ?? "",
    component: params.get("component") ?? "",
    group: params.get("group") ?? "",
    status: params.get("status") ?? "",
    credits: params.get("credits") ?? "",
    offering: params.get("offering") ?? "",
    selected: params.get("selected"),
  };
}

function writePreference(params: URLSearchParams, key: string, value: string | null) {
  if (value) params.set(key, value);
  else params.delete(key);
}

function mapStorageKey(map: CurriculumMap) {
  return `curriculum-map-preferences-v1:${map.revision.plan_code}`;
}

function evidenceText(item: MapRequirement["evidence"][number]) {
  return `${item.source_title} · ${item.locator}${item.page ? ` · página ${item.page}` : ""}`;
}

function EvidenceList({ items }: { items: MapRequirement["evidence"] }) {
  if (!items.length) {
    return <p className="muted-copy">No hay un snapshot de evidencia accesible para este dato.</p>;
  }
  return (
    <ul className="map-evidence-list">
      {items.map((item) => (
        <li key={item.reference}>
          <strong>{evidenceText(item)}</strong>
          {item.excerpt ? <span>{item.excerpt}</span> : null}
          {item.annotation ? <small>{item.annotation}</small> : null}
          {item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">Abrir fuente externa</a> : null}
        </li>
      ))}
    </ul>
  );
}

function FilterBar({
  map,
  preferences,
  visibleCount,
  onChange,
  onReset,
}: {
  map: CurriculumMap;
  preferences: MapPreferences;
  visibleCount: number;
  onChange: (key: keyof MapPreferences, value: string | null) => void;
  onReset: () => void;
}) {
  const credits = [...new Set(map.courses.map((course) => course.credits).filter((value): value is number => value !== null))].sort((a, b) => a - b);
  return (
    <section className="curriculum-filter-bar panel" aria-labelledby="curriculum-filters-title">
      <div className="curriculum-filter-heading">
        <div>
          <p className="eyebrow">Exploración</p>
          <h2 id="curriculum-filters-title">Filtra sin perder el contexto</h2>
        </div>
        <Button variant="quiet" type="button" onClick={onReset}><RotateCcw size={15} aria-hidden="true" /> Restablecer</Button>
      </div>
      <div className="curriculum-filter-grid">
        <label className="field-group curriculum-search-field">
          <span>Buscar por código o nombre</span>
          <input type="search" value={preferences.query} onChange={(event) => onChange("query", event.target.value || null)} placeholder="Ej. probabilidad" />
        </label>
        <label className="field-group">
          <span>Componente</span>
          <select value={preferences.component} onChange={(event) => onChange("component", event.target.value || null)}>
            <option value="">Todos</option>
            {map.components.map((component) => <option key={component.code} value={component.code}>{component.label}</option>)}
          </select>
        </label>
        <label className="field-group">
          <span>Agrupación</span>
          <select value={preferences.group} onChange={(event) => onChange("group", event.target.value || null)}>
            <option value="">Todas</option>
            {map.groups.map((group) => <option key={group.code} value={group.code}>{group.label}</option>)}
          </select>
        </label>
        <label className="field-group">
          <span>Estado personal</span>
          <select value={preferences.status} onChange={(event) => onChange("status", event.target.value || null)}>
            <option value="">Todos</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="field-group">
          <span>Créditos</span>
          <select value={preferences.credits} onChange={(event) => onChange("credits", event.target.value || null)}>
            <option value="">Todos</option>
            {credits.map((credit) => <option key={credit} value={credit}>{credit} créditos</option>)}
          </select>
        </label>
        <label className="field-group">
          <span>Oferta del período</span>
          <select value={preferences.offering} onChange={(event) => onChange("offering", event.target.value || null)}>
            <option value="">Todas</option>
            <option value="AVAILABLE">Con oferta registrada</option>
            <option value="NOT_REPORTED">Sin oferta registrada</option>
            <option value="UNKNOWN">Por seleccionar</option>
          </select>
        </label>
      </div>
      <p className="curriculum-filter-result" aria-live="polite">{visibleCount} cursos visibles · {map.courses.length} en la revisión</p>
    </section>
  );
}

function MapLegend() {
  return (
    <section className="curriculum-legend panel" aria-labelledby="curriculum-legend-title">
      <div>
        <p className="eyebrow">Lectura de la malla</p>
        <h2 id="curriculum-legend-title">Leyenda accesible</h2>
      </div>
      <div className="curriculum-legend-items">
        {Object.entries(statusLabels).map(([value, label]) => <span key={value}><StatusBadge tone={toneFor(value)} label={label} /></span>)}
        <span className="legend-context legend-context-selected">Seleccionado</span>
        <span className="legend-context legend-context-related">Dependencia o desbloqueo directo</span>
        <span className="legend-context legend-context-dimmed">Fuera del contexto seleccionado</span>
      </div>
    </section>
  );
}

function CourseDetailPanel({
  course,
  map,
  onSelect,
  headingRef,
}: {
  course: MapCourse;
  map: CurriculumMap;
  onSelect: (code: string | null) => void;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
}) {
  return (
    <aside className="curriculum-course-detail panel" aria-labelledby="curriculum-course-detail-title">
      <div className="curriculum-detail-heading">
        <div>
          <p className="eyebrow">Ficha de asignatura</p>
          <span className="course-code-label">{course.code}</span>
        </div>
        <button className="icon-button" type="button" onClick={() => onSelect(null)} aria-label="Cerrar ficha de asignatura"><X size={18} aria-hidden="true" /></button>
      </div>
      <h2 id="curriculum-course-detail-title" ref={headingRef} tabIndex={-1}>{course.name}</h2>
      <div className="curriculum-detail-status-row">
        <CourseStatusBadge tone={toneFor(course.personal_status)} label={statusLabel(course.personal_status)} />
        <span className="tag tag-outline">{course.credits === null ? "Créditos por verificar" : `${course.credits} créditos`}</span>
      </div>
      {course.status_reason ? <p className="muted-copy">Razón del estado: {course.status_reason}</p> : null}

      <dl className="curriculum-detail-facts">
        <div><dt>Nivel de dependencias</dt><dd>{course.dependency_depth_label}</dd></div>
        <div><dt>Oferta</dt><dd><StatusBadge tone={toneFor(course.offering_state)} label={offeringLabels[course.offering_state] ?? course.offering_state} /></dd></div>
        <div><dt>Componentes</dt><dd>{course.component_codes.join(", ") || "Sin agrupación declarada"}</dd></div>
      </dl>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-counts-title">
        <h3 id="curriculum-counts-title">Cuenta para</h3>
        {course.group_labels.length ? <div className="curriculum-chip-list">{course.group_labels.map((label) => <RequirementChip key={label} label={label} />)}</div> : <p className="muted-copy">La fuente no declaró una agrupación para esta asignatura.</p>}
      </section>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-requirements-title">
        <h3 id="curriculum-requirements-title">Requisitos para cursarla</h3>
        {course.requirements.length ? (
          <div className="curriculum-requirement-list">
            {course.requirements.map((requirement) => <RequirementDetail key={requirement.code} requirement={requirement} onSelect={onSelect} />)}
          </div>
        ) : <UnknownState title="Requisito no publicado" description="No hay una regla de matrícula registrada para esta asignatura. La elegibilidad no se infiere." />}
      </section>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-dependencies-title">
        <h3 id="curriculum-dependencies-title">Dependencias directas</h3>
        {course.dependencies.length ? <CourseCodeList codes={course.dependencies} onSelect={onSelect} /> : <p className="muted-copy">No se declararon dependencias directas.</p>}
      </section>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-unlocks-title">
        <h3 id="curriculum-unlocks-title">Desbloquea directamente</h3>
        {course.unlocks_directly.length ? <CourseCodeList codes={course.unlocks_directly} onSelect={onSelect} direction="down" /> : <p className="muted-copy">No hay desbloqueos directos en esta revisión.</p>}
      </section>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-offering-title">
        <h3 id="curriculum-offering-title">Oferta registrada</h3>
        {course.offerings.length ? <ul className="map-simple-list">{course.offerings.map((offering) => <li key={`${offering.term_code}-${offering.status}`}>{offering.term_code} · {offering.status} · {offering.section_count} secciones</li>)}</ul> : <p className="muted-copy">{map.offering_context.note}</p>}
      </section>

      <section className="curriculum-detail-section" aria-labelledby="curriculum-evidence-title">
        <h3 id="curriculum-evidence-title">Evidencia y procedencia</h3>
        <EvidencePopover title="Ver evidencia archivada"><EvidenceList items={course.source_evidence} /></EvidencePopover>
      </section>

      <div className="curriculum-detail-actions">
        <Link className="button button-secondary" href={`/audit?course=${encodeURIComponent(course.code)}`}>Abrir auditoría</Link>
        <Link className="button button-secondary" href={`/graph?selected=${encodeURIComponent(course.code)}`}>Abrir grafo</Link>
        <span className="muted-copy">Añadir a escenario se habilita en el planificador.</span>
      </div>
    </aside>
  );
}

function RequirementDetail({ requirement, onSelect }: { requirement: MapRequirement; onSelect: (code: string | null) => void }) {
  return (
    <article className="curriculum-requirement-card">
      <div className="course-card-header"><span className="course-code-label">{requirement.code}</span><StatusBadge tone={toneFor(requirement.status)} label={statusLabel(requirement.status)} /></div>
      <p>{requirement.purpose} · {requirement.explanation_key}</p>
      {requirement.note ? <small>{requirement.note}</small> : null}
      {requirement.dependencies.length ? <CourseCodeList codes={requirement.dependencies} onSelect={onSelect} /> : null}
      <details className="map-ast-details">
        <summary>Ver regla y evidencia</summary>
        <pre>{JSON.stringify(requirement.ast, null, 2)}</pre>
        <EvidenceList items={requirement.evidence} />
      </details>
    </article>
  );
}

function CourseCodeList({ codes, onSelect, direction = "up" }: { codes: string[]; onSelect: (code: string | null) => void; direction?: "up" | "down" }) {
  return (
    <ul className="map-course-code-list">
      {codes.map((code) => <li key={code}><button type="button" onClick={() => onSelect(code)}><span className="course-code-label">{code}</span><span>{direction === "up" ? <ArrowUp size={14} aria-hidden="true" /> : <ArrowDown size={14} aria-hidden="true" />}</span></button></li>)}
    </ul>
  );
}

function courseContext(course: MapCourse, selected: MapCourse | null): "selected" | "dependency" | "unlock" | "neutral" {
  if (!selected) return "neutral";
  if (course.code === selected.code) return "selected";
  if (selected.dependencies.includes(course.code)) return "dependency";
  if (selected.unlocks_directly.includes(course.code)) return "unlock";
  return "neutral";
}

function RenderCourseCard({ course, selected, onSelect }: { course: MapCourse; selected: MapCourse | null; onSelect: (code: string) => void }) {
  const context = courseContext(course, selected);
  return (
    <CourseCard
      code={course.code}
      name={course.name}
      credits={course.credits}
      status={toneFor(course.personal_status)}
      statusLabel={statusLabel(course.personal_status)}
      metadata={[course.component_codes.join(", "), course.group_labels[0], offeringLabels[course.offering_state]].filter(Boolean).join(" · ")}
      selected={context === "selected"}
      dimmed={Boolean(selected && context === "neutral")}
      context={context}
      onSelect={() => onSelect(course.code)}
      action={<button className="small-link map-course-open" type="button" onClick={() => onSelect(course.code)}>Ver ficha <ChevronRight size={14} aria-hidden="true" /></button>}
    />
  );
}

function DependencyDepthLayout({ courses, selected, onSelect }: { courses: MapCourse[]; selected: MapCourse | null; onSelect: (code: string) => void }) {
  const levels = [...new Set(courses.map((course) => course.dependency_depth).filter((depth): depth is number => depth !== null))].sort((a, b) => a - b);
  const undetermined = courses.filter((course) => course.dependency_depth === null);
  return (
    <div className="curriculum-depth-layout">
      {levels.map((level) => (
        <section className="curriculum-depth-column" key={level} aria-labelledby={`dependency-level-${level}`}>
          <div className="curriculum-column-heading"><span className="depth-marker">{level}</span><div><p className="eyebrow">Orden derivado</p><h3 id={`dependency-level-${level}`}>Nivel de dependencias {level}</h3></div></div>
          <CurriculumGrid label={`Cursos del nivel de dependencias ${level}`}>{courses.filter((course) => course.dependency_depth === level).map((course) => <RenderCourseCard key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</CurriculumGrid>
        </section>
      ))}
      {undetermined.length ? <section className="curriculum-depth-column curriculum-depth-unknown" aria-labelledby="dependency-level-unknown"><div className="curriculum-column-heading"><span className="depth-marker">?</span><div><p className="eyebrow">Estado epistemológico</p><h3 id="dependency-level-unknown">Nivel no determinable</h3></div></div><CurriculumGrid label="Cursos sin nivel de dependencia determinable">{undetermined.map((course) => <RenderCourseCard key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</CurriculumGrid></section> : null}
    </div>
  );
}

function ComponentLanesLayout({ courses, components, groups, selected, onSelect }: { courses: MapCourse[]; components: MapComponent[]; groups: MapGroup[]; selected: MapCourse | null; onSelect: (code: string) => void }) {
  return (
    <div className="curriculum-component-lanes">
      {components.map((component) => {
        const componentGroups = groups.filter((group) => group.component === component.code);
        return <section className="curriculum-component-lane" key={component.code} aria-labelledby={`component-lane-${component.code}`}><div className="curriculum-column-heading"><span className="component-marker">{component.code.slice(0, 1)}</span><div><p className="eyebrow">Componente · {component.required_credits} créditos</p><h3 id={`component-lane-${component.code}`}>{component.label}</h3></div></div>{componentGroups.map((group) => { const groupCourses = courses.filter((course) => course.group_codes.includes(group.code)); return <section className="curriculum-group-lane" key={group.code} aria-labelledby={`group-lane-${group.code}`}><div className="curriculum-group-heading"><h4 id={`group-lane-${group.code}`}>{group.label}</h4><span>{group.required_credits} créditos</span></div><CurriculumGrid label={`Cursos de ${group.label}`}>{groupCourses.map((course) => <RenderCourseCard key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</CurriculumGrid>{groupCourses.length === 0 ? <p className="muted-copy">Ningún curso coincide con los filtros actuales.</p> : null}</section>;})}</section>;
      })}
    </div>
  );
}

function DecisionCourseTile({ course, selected, onSelect }: { course: MapCourse; selected: MapCourse | null; onSelect: (code: string) => void }) {
  const context = courseContext(course, selected);
  return (
    <button className={`decision-course decision-course-${toneFor(course.personal_status)} decision-context-${context}`} type="button" data-course-code={course.code} aria-pressed={context === "selected"} onClick={() => onSelect(course.code)}>
      <span className="decision-course-topline"><span>{course.code}</span><StatusBadge tone={toneFor(course.personal_status)} label={statusLabel(course.personal_status)} /></span>
      <strong>{course.name}</strong>
      <small>{course.credits === null ? "Créditos por verificar" : `${course.credits} créditos`}{course.group_labels[0] ? ` · ${course.group_labels[0]}` : ""}</small>
    </button>
  );
}

function StudentDecisionHeader({ map, counts, onStatus }: { map: CurriculumMap; counts: Record<string, number>; onStatus: (status: string) => void }) {
  const summaries = [
    ["PASSED", "Aprobadas", "Lo que ya cerraste"],
    ["IN_PROGRESS", "En curso", "Tu carga actual"],
    ["ELIGIBLE", "Matriculables", "Regla verificada"],
    ["BLOCKED", "Bloqueadas", "Aún tienen requisitos"],
    ["UNKNOWN", "Por revisar", "Falta evidencia o contexto"],
  ] as const;
  return (
    <section className="decision-header" aria-labelledby="decision-map-title">
      <div className="decision-header-copy">
        <p className="eyebrow accent">Estadística · Plan {map.revision.plan_code}</p>
        <h1 id="decision-map-title">Tu malla, en una sola vista.</h1>
        <p>{map.personal.available ? "Distingue lo aprobado, lo que cursas, lo que puedes matricular y lo que todavía está bloqueado." : "Explora la estructura del plan. Inicia sesión con una matrícula vinculada para ver decisiones personales."}</p>
      </div>
      <div className="decision-status-strip" aria-label="Resumen del estado de asignaturas">
        {summaries.map(([status, label, helper]) => <button key={status} type="button" onClick={() => onStatus(status)} className={`decision-stat decision-stat-${toneFor(status)}`}><span>{label}</span><strong>{counts[status] ?? 0}</strong><small>{helper}</small></button>)}
      </div>
    </section>
  );
}

function EnrollmentDecision({ courses, selected, onSelect, onShowUnknown }: { courses: MapCourse[]; selected: MapCourse | null; onSelect: (code: string) => void; onShowUnknown: () => void }) {
  const eligible = courses.filter((course) => course.personal_status === "ELIGIBLE");
  const inProgress = courses.filter((course) => course.personal_status === "IN_PROGRESS");
  return (
    <section className="enrollment-decision panel" aria-labelledby="enrollment-decision-title">
      <div className="enrollment-decision-copy">
        <p className="eyebrow">Tu siguiente decisión</p>
        <h2 id="enrollment-decision-title">Qué puedes matricular ahora</h2>
        <p>{eligible.length ? `${eligible.length} asignaturas tienen elegibilidad confirmada con las reglas y la historia disponibles.` : "No hay una elegibilidad confirmada todavía. Esto no significa que no puedas matricular: hay reglas o datos pendientes de verificar."}</p>
        <div className="enrollment-decision-actions">
          {eligible.length ? <Link className="button button-primary" href="/planner">Armar mi próximo período <ArrowRight size={15} aria-hidden="true" /></Link> : <button className="button button-secondary" type="button" onClick={onShowUnknown}>Ver qué falta verificar</button>}
          <Link className="text-link" href="/history">Corregir mi historia</Link>
        </div>
      </div>
      <div className="enrollment-course-list">
        {eligible.slice(0, 6).map((course) => <DecisionCourseTile key={course.code} course={course} selected={selected} onSelect={onSelect} />)}
        {!eligible.length && inProgress.length ? <div className="enrollment-current"><span>Ahora estás cursando</span>{inProgress.map((course) => <DecisionCourseTile key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</div> : null}
        {!eligible.length && !inProgress.length ? <div className="decision-empty"><strong>Primero necesitamos una historia confiable.</strong><span>Registra o importa tus asignaturas para calcular la elegibilidad sin adivinar.</span></div> : null}
      </div>
    </section>
  );
}

function MandatoryJourney({ courses, selected, onSelect }: { courses: MapCourse[]; selected: MapCourse | null; onSelect: (code: string) => void }) {
  const mandatory = courses.filter((course) => course.membership_roles.includes("MANDATORY"));
  const depths = [...new Set(mandatory.map((course) => course.dependency_depth).filter((depth): depth is number => depth !== null))].sort((a, b) => a - b);
  const unknownDepth = mandatory.filter((course) => course.dependency_depth === null);
  return (
    <section className="decision-section mandatory-journey" aria-labelledby="mandatory-journey-title">
      <div className="decision-section-heading"><div><p className="eyebrow">Ruta principal</p><h2 id="mandatory-journey-title">Las obligatorias que sostienen el plan</h2><p>El orden muestra dependencias, no semestres oficiales. Lee de izquierda a derecha.</p></div><span className="decision-count">{mandatory.length} obligatorias</span></div>
      <div className="mandatory-track">
        {depths.map((depth) => <section className="mandatory-stage" key={depth} aria-labelledby={`mandatory-stage-${depth}`}><div className="mandatory-stage-heading"><span>{String(depth + 1).padStart(2, "0")}</span><h3 id={`mandatory-stage-${depth}`}>Momento {depth + 1}</h3></div><div className="mandatory-stage-courses">{mandatory.filter((course) => course.dependency_depth === depth).map((course) => <DecisionCourseTile key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</div></section>)}
        {unknownDepth.length ? <section className="mandatory-stage mandatory-stage-unknown"><div className="mandatory-stage-heading"><span>?</span><h3>Orden por verificar</h3></div><div className="mandatory-stage-courses">{unknownDepth.map((course) => <DecisionCourseTile key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</div></section> : null}
      </div>
    </section>
  );
}

function ChoicePools({ courses, groups, selected, onSelect }: { courses: MapCourse[]; groups: MapGroup[]; selected: MapCourse | null; onSelect: (code: string) => void }) {
  const optionCourses = courses.filter((course) => !course.membership_roles.includes("MANDATORY") && course.group_codes.length);
  return (
    <section className="decision-section choice-pools" aria-labelledby="choice-pools-title">
      <div className="decision-section-heading"><div><p className="eyebrow">Elecciones del plan</p><h2 id="choice-pools-title">Escoge dentro de cada agrupación</h2><p>No debes cursar todas estas asignaturas. Cada bloque es un banco de opciones para completar los créditos exigidos.</p></div><span className="decision-count">{optionCourses.length} opciones</span></div>
      <div className="choice-pool-grid">
        {groups.map((group) => {
          const groupCourses = optionCourses.filter((course) => course.group_codes.includes(group.code));
          if (!groupCourses.length) return null;
          const activeCount = groupCourses.filter((course) => ["PASSED", "IN_PROGRESS", "ELIGIBLE"].includes(course.personal_status)).length;
          return <details className="choice-pool panel" key={group.code} open={activeCount > 0}><summary><span><strong>{group.label}</strong><small>Completa {group.required_credits} créditos dentro de este bloque</small></span><span>{groupCourses.length} opciones</span></summary><div className="choice-pool-courses">{groupCourses.map((course) => <DecisionCourseTile key={course.code} course={course} selected={selected} onSelect={onSelect} />)}</div></details>;
        })}
      </div>
    </section>
  );
}

function LayoutContextNotice({ layout }: { layout: NonNullable<CurriculumMap["layout_policy"]["available_layouts"][number]> | undefined }) {
  if (!layout || layout.id === "dependency-depth" || layout.id === "component-lanes") return null;
  if (layout.id === "suggested-path") {
    return <div className="curriculum-layout-notice"><Alert><strong>Ruta sugerida pendiente de planificación.</strong> Esta revisión no contiene todavía un escenario optimizado ni restricciones de planificación. Se muestra una referencia por nivel de dependencias; no es una recomendación de cursado.</Alert></div>;
  }
  if (layout.id === "user-scenario") {
    return <div className="curriculum-layout-notice"><Alert><strong>Escenario personal no seleccionado.</strong> Este layout requiere un plan guardado por el estudiante. Se muestra una referencia por nivel de dependencias hasta que exista un escenario explícito.</Alert></div>;
  }
  return <div className="curriculum-layout-notice"><Alert><strong>Layout no disponible para esta revisión.</strong> Se muestra la referencia por nivel de dependencias y se conserva la etiqueta de layout para no inventar una interpretación normativa.</Alert></div>;
}

function CurriculumMapUnavailable({ message }: { message: string }) {
  return <section className="panel curriculum-map-unavailable"><EmptyState title="La malla no está disponible" description={message} action={<Link className="button button-primary" href="/">Volver al inicio</Link>} /></section>;
}

export function CurriculumMapPage({ map, failureMessage, printMode = false }: { map: CurriculumMap | null; failureMessage?: string; printMode?: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const defaultLayout = map?.layout_policy.available_layouts[0]?.id ?? "dependency-depth";
  const [preferences, setPreferences] = useState<MapPreferences>(() => readMapPreferences(new URLSearchParams(searchParams.toString()), defaultLayout));
  const [preferencesReady, setPreferencesReady] = useState(false);
  const courseDetailHeadingRef = useRef<HTMLHeadingElement>(null);
  const previousSelectedRef = useRef<string | null>(null);
  const selectionReturnRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!map) return;
    const stored = window.localStorage.getItem(mapStorageKey(map));
    const urlParams = new URLSearchParams(searchParams.toString());
    const urlPreferences = readMapPreferences(urlParams, defaultLayout);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<MapPreferences>;
        const keys: Array<keyof MapPreferences> = ["layout", "query", "component", "group", "status", "credits", "offering", "selected"];
        window.queueMicrotask(() => setPreferences((current) => {
          const merged = { ...current, ...parsed };
          for (const key of keys) {
            if (urlParams.has(key)) Object.assign(merged, { [key]: urlPreferences[key] });
          }
          return merged;
        }));
      } catch {
        window.localStorage.removeItem(mapStorageKey(map));
      }
    }
    window.queueMicrotask(() => setPreferencesReady(true));
  }, [defaultLayout, map, searchParams]);

  useEffect(() => {
    if (!map || !preferencesReady || printMode) return;
    window.localStorage.setItem(mapStorageKey(map), JSON.stringify(preferences));
    const next = new URLSearchParams(searchParams.toString());
    writePreference(next, "layout", preferences.layout === defaultLayout ? null : preferences.layout);
    writePreference(next, "q", preferences.query);
    writePreference(next, "component", preferences.component);
    writePreference(next, "group", preferences.group);
    writePreference(next, "status", preferences.status);
    writePreference(next, "credits", preferences.credits);
    writePreference(next, "offering", preferences.offering);
    writePreference(next, "selected", preferences.selected);
    const query = next.toString();
    const current = searchParams.toString();
    if (query !== current) router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [defaultLayout, map, pathname, preferences, preferencesReady, printMode, router, searchParams]);

  const visibleCourses = useMemo(() => {
    if (!map) return [];
    const query = preferences.query.trim().toLocaleLowerCase("es-CO");
    return map.courses.filter((course) => {
      const matchesQuery = !query || `${course.code} ${course.name}`.toLocaleLowerCase("es-CO").includes(query);
      const matchesComponent = !preferences.component || course.component_codes.includes(preferences.component);
      const matchesGroup = !preferences.group || course.group_codes.includes(preferences.group);
      const matchesStatus = !preferences.status || course.personal_status === preferences.status;
      const matchesCredits = !preferences.credits || String(course.credits) === preferences.credits;
      const matchesOffering = !preferences.offering || course.offering_state === preferences.offering;
      return matchesQuery && matchesComponent && matchesGroup && matchesStatus && matchesCredits && matchesOffering;
    });
  }, [map, preferences]);
  const selected = visibleCourses.find((course) => course.code === preferences.selected) ?? null;
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const course of map?.courses ?? []) counts[course.personal_status] = (counts[course.personal_status] ?? 0) + 1;
    return counts;
  }, [map]);
  useEffect(() => {
    const selectedCode = selected?.code ?? null;
    if (selectedCode && selectedCode !== previousSelectedRef.current) {
      window.queueMicrotask(() => courseDetailHeadingRef.current?.focus());
    } else if (!selectedCode && previousSelectedRef.current) {
      window.queueMicrotask(() => selectionReturnRef.current?.focus());
    }
    previousSelectedRef.current = selectedCode;
  }, [selected]);

  if (!map) return <CurriculumMapUnavailable message={failureMessage ?? "La API no devolvió una revisión curricular verificable."} />;

  const layout = map.layout_policy.available_layouts.find((item) => item.id === preferences.layout) ?? map.layout_policy.available_layouts[0];
  const updatePreference = (key: keyof MapPreferences, value: string | null) => {
    if (key === "selected" && value && !selected) {
      const activeElement = document.activeElement;
      selectionReturnRef.current = activeElement instanceof HTMLElement ? activeElement : null;
    }
    setPreferences((current) => ({ ...current, [key]: value ?? "" }));
  };
  const reset = () => setPreferences((current) => ({ ...current, layout: defaultLayout, query: "", component: "", group: "", status: "", credits: "", offering: "", selected: null }));

  return (
    <div className={`curriculum-map-page${printMode ? " curriculum-map-print" : ""}`} data-layout={layout?.id ?? defaultLayout}>
      {!printMode ? <StudentDecisionHeader map={map} counts={statusCounts} onStatus={(status) => updatePreference("status", status)} /> : null}
      {!printMode ? <EnrollmentDecision courses={map.courses} selected={selected} onSelect={(code) => updatePreference("selected", code)} onShowUnknown={() => updatePreference("status", "UNKNOWN")} /> : null}
      {!printMode && preferences.selected && !selected ? <Alert tone="info"><strong>La asignatura seleccionada quedó fuera del filtro actual.</strong> Restablece la exploración para volver a mostrarla.</Alert> : null}
      {!printMode ? <MandatoryJourney courses={visibleCourses} selected={selected} onSelect={(code) => updatePreference("selected", code)} /> : <DependencyDepthLayout courses={visibleCourses} selected={selected} onSelect={(code) => updatePreference("selected", code)} />}
      {!printMode ? <ChoicePools courses={visibleCourses} groups={map.groups} selected={selected} onSelect={(code) => updatePreference("selected", code)} /> : null}
      {!printMode ? (
        <details className="curriculum-explorer panel">
          <summary><span><strong>Explorar y filtrar el plan completo</strong><small>Búsqueda, estado, agrupación, otras vistas, impresión y procedencia</small></span><span>{visibleCourses.length}/{map.courses.length}</span></summary>
          <div className="curriculum-explorer-body">
            <section className="curriculum-map-toolbar"><div className="field-group"><label htmlFor="curriculum-layout">Vista de exploración</label><select id="curriculum-layout" value={layout?.id ?? defaultLayout} onChange={(event) => updatePreference("layout", event.target.value)}>{map.layout_policy.available_layouts.map((item) => <option key={item.id} value={item.id}>{item.label} · no normativo</option>)}</select></div><div className="curriculum-toolbar-actions"><button className="button button-secondary" type="button" onClick={() => window.print()}><Printer size={15} aria-hidden="true" /> Imprimir</button><Link className="button button-secondary" href={map.links.print}>Vista de impresión</Link></div></section>
            <FilterBar map={map} preferences={preferences} visibleCount={visibleCourses.length} onChange={updatePreference} onReset={reset} />
            <MapLegend />
            <LayoutContextNotice layout={layout} />
            <div className="curriculum-legacy-view">{layout?.id === "component-lanes" ? <ComponentLanesLayout courses={visibleCourses} components={map.components} groups={map.groups} selected={selected} onSelect={(code) => updatePreference("selected", code)} /> : <DependencyDepthLayout courses={visibleCourses} selected={selected} onSelect={(code) => updatePreference("selected", code)} />}</div>
          </div>
        </details>
      ) : null}
      <section className={`curriculum-map-layout${selected ? " has-selection" : ""}`} aria-label="Detalle contextual de la malla">
        <div className="curriculum-map-main">{!visibleCourses.length ? <section className="panel curriculum-map-empty"><EmptyState title="Ningún curso coincide" description="Ajusta o restablece los filtros para recuperar el contexto de la malla." action={<Button variant="secondary" type="button" onClick={reset}>Restablecer filtros</Button>} /></section> : null}</div>
        {selected ? <CourseDetailPanel course={selected} map={map} onSelect={(code) => updatePreference("selected", code)} headingRef={courseDetailHeadingRef} /> : null}
      </section>
      <footer className="curriculum-map-footer"><span><StatusBadge tone={map.revision.status === "PUBLISHED" ? "passed" : "unknown"} label={map.revision.status === "PUBLISHED" ? "Revisión publicada" : "Revisión en proceso editorial"} /> {map.revision.revision_code} · {map.revision.total_required_credits} créditos</span><Link href={map.links.sources}>Ver procedencia</Link><span>{map.personal?.available ? "Estados calculados con tu historia" : "Sin estado personal en esta sesión"}</span></footer>
    </div>
  );
}

export { CurriculumMapUnavailable };
