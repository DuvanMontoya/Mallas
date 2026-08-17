"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { DependencyGraph } from "@/lib/api";

import { Alert, EmptyState, StatusBadge, UnknownState } from "./ui";
import { DependencyGraphCanvas } from "./dependency-graph-canvas";
import type { StatusTone } from "./ui/status-badge";

const statusLabels: Record<string, string> = {
  PASSED: "Aprobado",
  IN_PROGRESS: "En curso",
  ELIGIBLE: "Puedes cursarlo",
  BLOCKED: "Bloqueado",
  UNKNOWN: "Por verificar",
  NOT_ASSESSED: "Sin estado personal",
};

const edgeLabels: Record<string, string> = {
  PREREQUISITE: "Prerrequisito",
  COREQUISITE: "Correquisito",
  CONDITION_INPUT: "Entrada de condición",
  ALTERNATIVE_INPUT: "Alternativa",
  THRESHOLD_INPUT: "Entrada de umbral",
  CONDITION_SATISFIES: "Condición para cursar",
};

function statusLabel(value: string) {
  return statusLabels[value] ?? value.replaceAll("_", " ");
}

function statusTone(value: string): StatusTone {
  if (value === "PASSED") return "passed";
  if (value === "IN_PROGRESS") return "in-progress";
  if (value === "ELIGIBLE") return "eligible";
  if (value === "BLOCKED") return "blocked";
  if (value === "UNKNOWN") return "unknown";
  return "neutral";
}

function relationText(relation: DependencyGraph["direct_relations"][number]) {
  return `${edgeLabels[relation.relation_type] ?? relation.relation_type} · ${relation.semantic.replaceAll("_", " ")} · ${relation.requirement_code}`;
}

function relationList(
  relations: DependencyGraph["direct_relations"],
  courseCode: string,
  direction: "in" | "out",
  onSelect: (code: string) => void,
) {
  const values = relations.filter((relation) => direction === "in" ? relation.target_course === courseCode : relation.source_course === courseCode);
  if (!values.length) return <p className="muted-copy">No hay relaciones directas declaradas.</p>;
  return (
    <ul className="graph-relation-list">
      {values.map((relation) => {
        const related = direction === "in" ? relation.source_course : relation.target_course;
        return (
          <li key={`${relation.requirement_code}-${related}-${relation.relation_type}`}>
            <button type="button" onClick={() => onSelect(related)}>
              <strong>{related}</strong>
              <span>{relationText(relation)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function GraphLegend() {
  return (
    <section className="dependency-graph-legend panel" aria-labelledby="dependency-graph-legend-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Leyenda accesible</p>
          <h2 id="dependency-graph-legend-title">Qué significa cada relación</h2>
        </div>
      </div>
      <ul className="graph-legend-list">
        <li><span className="graph-legend-swatch graph-legend-course" aria-hidden="true" /> Curso: una asignatura del plan.</li>
        <li><span className="graph-legend-swatch graph-legend-condition" aria-hidden="true" /> Condición: ALL, ANY, umbral, equivalencia o requisito externo.</li>
        <li><span className="graph-legend-line graph-legend-direct" aria-hidden="true" /> Relación directa declarada por una regla.</li>
        <li><span className="graph-legend-line graph-legend-transitive" aria-hidden="true" /> Ruta transitiva: se explica en el panel de análisis.</li>
      </ul>
    </section>
  );
}

function FocusPanel({ graph, onSelect, headingRef }: { graph: DependencyGraph; onSelect: (code: string) => void; headingRef: React.RefObject<HTMLHeadingElement | null> }) {
  const focus = graph.focus;
  if (!focus) {
    return (
      <aside className="dependency-graph-focus panel" aria-labelledby="dependency-focus-title">
        <p className="eyebrow">Análisis explicable</p>
        <h2 id="dependency-focus-title" ref={headingRef} tabIndex={-1}>Selecciona un curso</h2>
        <p>El grafo completo muestra condiciones y relaciones directas. Selecciona un curso para calcular ancestros, descendientes y rutas cortas de desbloqueo.</p>
        <UnknownState title="Sin foco seleccionado" description="El backend no inventa una ruta sin un curso de referencia." />
      </aside>
    );
  }

  return (
    <aside className="dependency-graph-focus panel" aria-labelledby="dependency-focus-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Foco contextual</p>
          <h2 id="dependency-focus-title" ref={headingRef} tabIndex={-1}>{focus.course_code}</h2>
          <p className="muted-copy">{focus.course_name}</p>
        </div>
        <StatusBadge tone="neutral" label="Sin modificar reglas" />
      </div>
      <section className="graph-focus-section" aria-labelledby="graph-prereq-title">
        <h3 id="graph-prereq-title">Prerrequisitos directos</h3>
        {relationList(focus.direct_prerequisites, focus.course_code, "in", onSelect)}
      </section>
      <section className="graph-focus-section" aria-labelledby="graph-coreq-title">
        <h3 id="graph-coreq-title">Correquisitos directos</h3>
        {focus.direct_corequisites.length ? relationList(focus.direct_corequisites, focus.course_code, "in", onSelect) : <p className="muted-copy">No hay correquisitos declarados.</p>}
      </section>
      <section className="graph-focus-section" aria-labelledby="graph-unlock-title">
        <h3 id="graph-unlock-title">Desbloqueos directos</h3>
        {relationList(focus.direct_unlocks, focus.course_code, "out", onSelect)}
      </section>
      <section className="graph-focus-section" aria-labelledby="graph-transitive-title">
        <h3 id="graph-transitive-title">Alcance transitivo</h3>
        <div className="graph-reachability-grid">
          <div><strong>Ancestros</strong><span>{focus.ancestors.length} cursos</span></div>
          <div><strong>Descendientes</strong><span>{focus.descendants.length} cursos</span></div>
        </div>
        <p className="muted-copy">La distancia cuenta cursos; las condiciones intermedias se conservan en cada ruta explicativa.</p>
        <ul className="graph-path-list">
          {focus.shortest_unlock_paths.slice(0, 12).map((path) => (
            <li key={path.target_course}>
              <button type="button" onClick={() => onSelect(path.target_course)}>
                <strong>{path.target_course}</strong>
                <span>{path.explanation}</span>
                <small>{path.direct ? "Desbloqueo directo" : `Ruta transitiva · ${path.distance} saltos`}</small>
              </button>
            </li>
          ))}
        </ul>
        {focus.shortest_unlock_paths.length > 12 ? <p className="muted-copy">Se muestran las primeras 12 rutas; usa filtros para reducir el contexto.</p> : null}
      </section>
      <div className="dependency-focus-actions">
        <Link className="button button-secondary" href={`/curriculum?selected=${encodeURIComponent(focus.course_code)}`}>Abrir ficha curricular</Link>
        <Link className="button button-secondary" href={`/audit?course=${encodeURIComponent(focus.course_code)}`}>Abrir auditoría</Link>
      </div>
    </aside>
  );
}

function TextualAlternative({ graph, visibleNodeIds, onSelect }: { graph: DependencyGraph; visibleNodeIds: Set<string>; onSelect: (code: string) => void }) {
  const nodes = graph.nodes.filter((node) => visibleNodeIds.has(node.id));
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const edges = graph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target));

  function nodeName(nodeId: string) {
    const node = nodeById.get(nodeId);
    if (!node) return nodeId;
    return node.course_code ? `${node.course_code} · ${node.label}` : node.label;
  }

  function edgeText(edge: DependencyGraph["edges"][number]) {
    const relation = edgeLabels[edge.kind] ?? edge.label;
    return `${relation} · ${edge.semantic.replaceAll("_", " ")} · ${edge.requirement_code}`;
  }

  return (
    <section className="dependency-graph-textual panel" aria-labelledby="dependency-textual-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Alternativa para lector de pantalla</p>
          <h2 id="dependency-textual-title">Lista textual de relaciones</h2>
        </div>
        <span className="tag tag-outline">{nodes.length} nodos visibles</span>
      </div>
      <p className="muted-copy">Esta lista conserva la distinción entre relaciones directas, condiciones y rutas transitivas. No depende de la posición del grafo ni del color.</p>
      {nodes.length ? (
        <ol className="graph-textual-list">
          {nodes.map((node) => {
            const incoming = edges.filter((edge) => edge.target === node.id);
            const outgoing = edges.filter((edge) => edge.source === node.id);
            const selectableCourse = node.kind === "COURSE" && node.course_code;
            const summary = `${node.kind === "CONDITION" ? "Condición" : "Curso"} · estado ${statusLabel(node.state)}${node.condition_type ? ` · tipo ${node.condition_type}` : ""}${node.epistemic_status ? ` · evidencia ${node.epistemic_status}` : ""}`;
            return (
              <li key={node.id} data-testid={`graph-textual-node-${node.id}`}>
                {selectableCourse ? (
                  <button data-testid={`graph-textual-course-${node.course_code}`} type="button" onClick={() => onSelect(node.course_code ?? "")}>
                    <strong>{node.course_code} · {node.label}</strong>
                    <StatusBadge tone={statusTone(node.state)} label={statusLabel(node.state)} />
                  </button>
                ) : (
                  <div className="graph-textual-node-heading">
                    <strong>{node.label}</strong>
                    <StatusBadge tone={statusTone(node.state)} label={statusLabel(node.state)} />
                  </div>
                )}
                <span>{summary} · requisito {node.requirement_code ?? "no especificado"}.</span>
                {incoming.length || outgoing.length ? (
                  <ul className="graph-relation-list">
                    {incoming.map((edge) => <li key={`in-${edge.id}`}>Recibe de <strong>{nodeName(edge.source)}</strong>: {edgeText(edge)}.</li>)}
                    {outgoing.map((edge) => <li key={`out-${edge.id}`}>Lleva a <strong>{nodeName(edge.target)}</strong>: {edgeText(edge)}.</li>)}
                  </ul>
                ) : <span>Sin relaciones directas visibles.</span>}
              </li>
            );
          })}
        </ol>
      ) : <EmptyState title="Ningún nodo coincide" description="Ajusta o restablece los filtros del grafo." />}
    </section>
  );
}

export function DependencyGraphExplorer({ graph, failureMessage }: { graph: DependencyGraph | null; failureMessage?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [component, setComponent] = useState("");
  const [nodeKind, setNodeKind] = useState("ALL");
  const [status, setStatus] = useState("");
  const [focusMode, setFocusMode] = useState(false);
  const focusHeadingRef = useRef<HTMLHeadingElement>(null);
  const previousFocusCourseRef = useRef<string | null>(null);

  const selectCourse = (code: string) => {
    router.replace(`/graph?selected=${encodeURIComponent(code)}`, { scroll: false });
  };

  const focusCourseCode = graph?.focus?.course_code ?? null;
  useEffect(() => {
    if (focusCourseCode && focusCourseCode !== previousFocusCourseRef.current) {
      window.queueMicrotask(() => focusHeadingRef.current?.focus());
    }
    previousFocusCourseRef.current = focusCourseCode;
  }, [focusCourseCode]);

  const componentOptions = useMemo(() => [...new Set(graph?.nodes.flatMap((node) => node.component_codes) ?? [])].sort(), [graph]);
  const statusOptions = useMemo(() => [...new Set(graph?.nodes.map((node) => node.state) ?? [])].sort(), [graph]);
  const focusNodeIds = useMemo(() => {
    if (!graph?.focus) return new Set<string>();
    const codes = new Set<string>([
      graph.focus.course_code,
      ...graph.focus.ancestors.map((item) => item.course_code),
      ...graph.focus.descendants.map((item) => item.course_code),
    ]);
    const ids = new Set<string>([...codes].map((code) => `course:${code}`));
    for (const path of graph.focus.shortest_unlock_paths) {
      for (const nodeId of path.node_ids) ids.add(nodeId);
    }
    return ids;
  }, [graph]);
  const visibleNodes = useMemo(() => {
    if (!graph) return [];
    const normalizedQuery = query.trim().toLocaleLowerCase("es-CO");
    return graph.nodes.filter((node) => {
      const matchesQuery = !normalizedQuery || `${node.course_code ?? ""} ${node.label} ${node.condition_type ?? ""}`.toLocaleLowerCase("es-CO").includes(normalizedQuery);
      const matchesComponent = !component || node.component_codes.includes(component);
      const matchesKind = nodeKind === "ALL" || node.kind === nodeKind;
      const matchesStatus = !status || node.state === status;
      const matchesFocus = !focusMode || !graph.focus || focusNodeIds.has(node.id);
      return matchesQuery && matchesComponent && matchesKind && matchesStatus && matchesFocus;
    });
  }, [component, focusMode, focusNodeIds, graph, nodeKind, query, status]);
  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((node) => node.id)), [visibleNodes]);
  const visibleEdges = useMemo(() => graph?.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)) ?? [], [graph, visibleNodeIds]);

  if (!graph) {
    return <section className="page-shell dependency-graph-page"><section className="panel"><EmptyState title="El grafo no está disponible" description={failureMessage ?? "La API no devolvió una proyección curricular verificable."} action={<Link className="button button-primary" href="/curriculum">Volver a la malla</Link>} /></section></section>;
  }

  return (
    <div className="page-shell dependency-graph-page">
      <section className="dependency-graph-hero panel">
        <div>
          <p className="eyebrow accent">Dependencias · {graph.revision.program_code}</p>
          <h1>Entiende qué desbloquea cada curso.</h1>
          <p>El grafo proyecta las reglas archivadas como cursos y condiciones. Puedes enfocar una asignatura, seguir rutas transitivas y leer la misma relación sin depender del dibujo.</p>
        </div>
        <div className="dependency-graph-meta"><span className="tag tag-outline">{graph.revision.revision_code}</span><span>{graph.nodes.length} nodos</span><span>{graph.edges.length} relaciones</span></div>
      </section>
      {graph.warnings.length ? <div className="dependency-graph-alerts">{graph.warnings.map((warning) => <Alert key={warning}><strong>{warning === "LAYOUTS_ARE_NOT_NORMATIVE" ? "La revisión usa layouts y relaciones visuales no normativas." : warning === "CURRICULUM_DEPENDENCY_CYCLE" ? "Hay un ciclo que requiere revisión administrativa." : warning === "GRAPH_FOCUS_NOT_FOUND" ? "El curso solicitado no pertenece a esta revisión." : warning}</strong></Alert>)}</div> : null}
      <section className="dependency-graph-toolbar panel" aria-labelledby="dependency-filter-title">
        <div className="section-heading"><div><p className="eyebrow">Exploración</p><h2 id="dependency-filter-title">Filtra y enfoca sin editar reglas</h2></div><span className="tag tag-outline" aria-live="polite">{visibleNodes.length} nodos · {visibleEdges.length} relaciones</span></div>
        <div className="dependency-filter-grid">
          <label className="field-group"><span>Buscar curso o condición</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Código, nombre o tipo" /></label>
          <label className="field-group"><span>Componente</span><select value={component} onChange={(event) => setComponent(event.target.value)}><option value="">Todos</option>{componentOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="field-group"><span>Tipo de nodo</span><select value={nodeKind} onChange={(event) => setNodeKind(event.target.value)}><option value="ALL">Todos</option><option value="COURSE">Cursos</option><option value="CONDITION">Condiciones</option></select></label>
          <label className="field-group"><span>Estado</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option>{statusOptions.map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}</select></label>
        </div>
        <label className="graph-focus-toggle"><input type="checkbox" checked={focusMode} onChange={(event) => setFocusMode(event.target.checked)} disabled={!graph.focus} /> <span>Modo foco: conservar sólo ancestros, descendientes y condiciones de la selección</span></label>
        <p className="muted-copy">Los nodos no se pueden arrastrar para cambiar reglas. React Flow sólo presenta la proyección; el backend y la evidencia siguen siendo la autoridad.</p>
      </section>
      <GraphLegend />
      <section className="dependency-graph-workspace" aria-label="Explorador de grafo curricular">
        <div className="dependency-graph-visual panel">
          {visibleNodes.length ? <DependencyGraphCanvas nodes={visibleNodes} edges={visibleEdges} onSelectCourse={selectCourse} /> : <EmptyState title="Ningún nodo coincide" description="Ajusta o restablece los filtros del grafo." />}
        </div>
        <FocusPanel graph={graph} onSelect={selectCourse} headingRef={focusHeadingRef} />
      </section>
      <p className="sr-only" role="status" aria-live="polite" data-testid="graph-focus-announcement">{graph.focus ? `Foco seleccionado: ${graph.focus.course_code}, ${graph.focus.course_name}.` : "No hay un curso seleccionado en el grafo."}</p>
      <TextualAlternative graph={graph} visibleNodeIds={visibleNodeIds} onSelect={selectCourse} />
      <section className="dependency-graph-cycles panel" aria-labelledby="dependency-cycles-title">
        <div className="section-heading"><div><p className="eyebrow">Gobernanza</p><h2 id="dependency-cycles-title">Ciclos de dependencia</h2></div><span className="tag tag-outline">{graph.cycles.length} detectados</span></div>
        {graph.cycles.length ? <ul className="graph-cycle-list">{graph.cycles.map((cycle) => <li key={cycle.cycle_id}><StatusBadge tone="blocked" label={cycle.severity} /><strong>{cycle.course_codes.join(" → ")}</strong><span>{cycle.explanation}</span></li>)}</ul> : <p className="muted-copy">No se detectaron ciclos en esta revisión. Si una revisión futura los contiene, se muestran como incidencia para revisión administrativa.</p>}
      </section>
      <footer className="dependency-graph-footer"><Link href={graph.links.curriculum}>Volver a la malla</Link><Link href={graph.links.sources}>Ver procedencia</Link><span>Proyección determinista · sin edición desde la vista estudiante</span></footer>
    </div>
  );
}
