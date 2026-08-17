"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useOptimistic, useState, useTransition } from "react";

import type { OfferingsReadModel, ScheduleEvaluation } from "@/lib/api";

const dayNames = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

type Offering = OfferingsReadModel["offerings"][number];
type Section = Offering["sections"][number];
type Meeting = Section["meetings"][number];

function dateLabel(value: string | null) {
  if (!value) return "fecha del período";
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium" }).format(new Date(value));
}

function sourceLabel(offering: Offering) {
  const retrieved = offering.source.retrieved_at
    ? `Fuente consultada ${dateLabel(offering.source.retrieved_at)}`
    : "Fuente y fecha no disponibles";
  return `${retrieved}. ${offering.source.source_name ?? "Origen no identificado"}.`;
}

function statusClass(value: string) {
  return value.toLowerCase().replaceAll("_", "-");
}

function freshnessLabel(value: string) {
  return { FRESH: "fresca", STALE: "antigua", UNKNOWN: "desconocida" }[value] ?? "por verificar";
}

function ScheduleRows({ meetings }: { meetings: Meeting[] }) {
  if (!meetings.length) return <p className="muted-copy">Horario no reportado para este grupo.</p>;
  return (
    <dl className="offering-schedule-grid">
      {meetings.map((meeting) => (
        <div key={String(meeting.id)}>
          <dt>{dayNames[meeting.day_of_week] ?? "Día no identificado"}</dt>
          <dd>
            {meeting.starts_at}–{meeting.ends_at} · {meeting.location || "Lugar no reportado"}
            {meeting.is_alternate ? " · sesión alterna" : ""}
            {meeting.starts_on || meeting.ends_on
              ? ` · ${dateLabel(meeting.starts_on)}–${dateLabel(meeting.ends_on)}`
              : ""}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function SectionCard({
  offering,
  section,
  selected,
  onToggle,
}: {
  offering: Offering;
  section: Section;
  selected: boolean;
  onToggle: (sectionId: string) => void;
}) {
  return (
    <article className="offering-section-card">
      <div className="offering-section-header">
        <div>
          <p className="eyebrow">Grupo {section.group_code}</p>
          <h3>{section.modality === "UNKNOWN" ? "Modalidad por verificar" : section.modality.replaceAll("_", " ")}</h3>
        </div>
        <label className="offering-select-section">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggle(String(section.id))}
            aria-label={`Seleccionar grupo ${section.group_code} de ${offering.course_code}`}
          />
          <span>Comparar horario</span>
        </label>
      </div>
      <div className="offering-section-badges">
        <span className={`offering-status-badge offering-status-${statusClass(section.schedulable_state)}`}>
          Horario: {section.schedulable_state === "NOT_EVALUATED" ? "sin evaluar" : section.schedulable_state}
        </span>
        <span className={`offering-status-badge offering-status-${statusClass(section.capacity.state)}`}>
          Cupo: {section.capacity.state === "UNKNOWN" ? "dato no reportado" : section.capacity.state}
        </span>
      </div>
      <ScheduleRows meetings={section.meetings} />
      <p className="muted-copy">{section.capacity.note}</p>
    </article>
  );
}

function OfferingCard({
  offering,
  selectedSectionIds,
  onToggleSection,
}: {
  offering: Offering;
  selectedSectionIds: Set<string>;
  onToggleSection: (sectionId: string) => void;
}) {
  return (
    <article className="offering-card panel">
      <div className="offering-card-header">
        <div>
          <p className="eyebrow">{offering.course_code} · {offering.credits ?? "—"} créditos</p>
          <h2>
            <Link href={`/curriculum?selected=${encodeURIComponent(offering.course_code)}`}>
              {offering.course_name}
            </Link>
          </h2>
        </div>
        <span className={`freshness-badge freshness-${statusClass(offering.source.freshness)}`}>
          Fuente {freshnessLabel(offering.source.freshness)}
        </span>
      </div>
      <p className="offering-source-note">{sourceLabel(offering)}</p>
      <div className="offering-state-row" aria-label={`Estados de ${offering.course_code}`}>
        <span className={`offering-status-badge offering-status-${statusClass(offering.eligibility_state)}`}>
          Académico: {offering.eligibility_state}
        </span>
        <span className={`offering-status-badge offering-status-${statusClass(offering.offered_state)}`}>
          Oferta: {offering.offered_state}
        </span>
        <span className={`offering-status-badge offering-status-${statusClass(offering.schedulable_state)}`}>
          Horario: sin evaluar
        </span>
      </div>
      {offering.eligibility_reasons.length ? (
        <details className="offering-reason-disclosure">
          <summary>Por qué el estado académico es {offering.eligibility_state.toLowerCase()}</summary>
          <ul>
            {offering.eligibility_reasons.slice(0, 4).map((reason) => (
              <li key={`${offering.id}-${String(reason.code ?? "reason")}`}>
                {String(reason.note ?? reason.explanation_key ?? reason.code ?? "Regla sin explicación")}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <div className="offering-section-list">
        {offering.sections.length ? (
          offering.sections.map((section) => (
            <SectionCard
              key={String(section.id)}
              offering={offering}
              section={section}
              selected={selectedSectionIds.has(String(section.id))}
              onToggle={onToggleSection}
            />
          ))
        ) : (
          <p className="muted-copy">La fuente reporta la asignatura, pero no sus grupos.</p>
        )}
      </div>
    </article>
  );
}

function ScheduleEvaluationPanel({ evaluation }: { evaluation: ScheduleEvaluation | null }) {
  if (!evaluation) {
    return (
      <section className="panel offerings-schedule-panel" aria-labelledby="offerings-schedule-title">
        <p className="eyebrow">ScheduleGrid</p>
        <h2 id="offerings-schedule-title">Compara grupos antes de planear</h2>
        <p className="muted-copy">Selecciona dos o más grupos. El backend compara intervalos, zona horaria y fechas parciales del período.</p>
      </section>
    );
  }
  return (
    <section className="panel offerings-schedule-panel" aria-labelledby="offerings-schedule-title">
      <p className="eyebrow">ScheduleGrid · {evaluation.term_code}</p>
      <h2 id="offerings-schedule-title">
        {evaluation.state === "CONFLICT" ? "Hay solapamientos" : evaluation.state === "SCHEDULABLE" ? "Horario compatible" : "Horario por verificar"}
      </h2>
      {evaluation.state === "CONFLICT" ? (
        <ul className="offering-conflict-list">
          {evaluation.conflicts.slice(0, 8).map((conflict) => (
            <li key={`${conflict.left_meeting_id}-${conflict.right_meeting_id}-${conflict.occurrence_date}`}>
              <strong>{conflict.occurrence_date}</strong>
              <span>Grupos {conflict.left_section_id.slice(0, 8)} y {conflict.right_section_id.slice(0, 8)} se solapan.</span>
            </li>
          ))}
        </ul>
      ) : evaluation.state === "UNKNOWN" ? (
        <ul className="offering-conflict-list">
          {evaluation.unknown_reasons.map((reason) => <li key={reason}>{reason}</li>)}
        </ul>
      ) : (
        <p className="muted-copy">No se encontraron solapamientos entre los grupos seleccionados en el período.</p>
      )}
      {evaluation.conflicts.length > 8 ? <p className="muted-copy">Se muestran los primeros 8 conflictos; el backend conserva todas las ocurrencias.</p> : null}
    </section>
  );
}

export function OfferingsExplorer({
  data,
  schedule,
  selectedSectionIds,
  failureMessage,
}: {
  data: OfferingsReadModel | null;
  schedule: ScheduleEvaluation | null;
  selectedSectionIds: string[];
  failureMessage?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [query, setQuery] = useState("");
  const [isPending, startTransition] = useTransition();
  const [selected, setSelected] = useOptimistic(
    new Set(selectedSectionIds),
    (_current: Set<string>, next: Set<string>) => next,
  );

  if (!data) {
    return (
      <div className="page-shell module-shell">
        <section className="panel module-panel" role="alert">
          <p className="eyebrow accent">Oferta académica</p>
          <h1>No se pudo cargar la oferta</h1>
          <p>{failureMessage ?? "El servicio no entregó una respuesta verificable."}</p>
        </section>
      </div>
    );
  }

  const termCode = data.selected_term_code ?? data.terms[0]?.code ?? "";
  const term = data.terms.find((item) => item.code === termCode);
  const visibleOfferings = data.offerings.filter((offering) => {
    if (termCode && offering.term.code !== termCode) return false;
    const normalized = query.trim().toLocaleLowerCase("es-CO");
    return !normalized || `${offering.course_code} ${offering.course_name}`.toLocaleLowerCase("es-CO").includes(normalized);
  });

  function changeTerm(nextTerm: string) {
    const params = new URLSearchParams(window.location.search);
    params.set("term", nextTerm);
    params.delete("sections");
    startTransition(() => router.replace(`${pathname}?${params.toString()}`));
  }

  function toggleSection(sectionId: string) {
    const next = new Set(selected);
    if (next.has(sectionId)) next.delete(sectionId);
    else next.add(sectionId);
    const params = new URLSearchParams(window.location.search);
    if (termCode) params.set("term", termCode);
    if (next.size) params.set("sections", Array.from(next).join(","));
    else params.delete("sections");
    startTransition(() => {
      setSelected(next);
      router.replace(`${pathname}?${params.toString()}`);
    });
  }

  return (
    <div className="offerings-page">
      <section className="panel offerings-hero">
        <div>
          <p className="eyebrow accent">Oferta · fuente temporal</p>
          <h1>Encuentra grupos sin confundir oferta con elegibilidad.</h1>
          <p>La malla responde qué exige el plan. Esta vista responde qué reportó una fuente para un período y si los grupos elegidos chocan en horario.</p>
        </div>
        <dl className="offerings-hero-meta">
          <div><dt>Período</dt><dd>{term?.code ?? "Sin seleccionar"}</dd></div>
          <div><dt>Estado</dt><dd>{term?.status ?? "UNKNOWN"}</dd></div>
          <div><dt>Fuente</dt><dd>{term?.source.freshness ?? "UNKNOWN"}</dd></div>
        </dl>
      </section>
      {failureMessage ? <p className="inline-error" role="alert">{failureMessage}</p> : null}
      <section className="panel offerings-toolbar" aria-labelledby="offerings-filter-title">
        <div className="section-heading"><div><p className="eyebrow">Exploración</p><h2 id="offerings-filter-title">Oferta por período</h2></div><span className="tag tag-outline">{visibleOfferings.length} asignaturas</span></div>
        <div className="offerings-filter-grid">
          <label className="field-group"><span>Período académico</span><select value={termCode} onChange={(event) => changeTerm(event.target.value)} disabled={isPending}><option value="">Todos los períodos</option>{data.terms.map((item) => <option key={String(item.id)} value={item.code}>{item.code} · {item.status}</option>)}</select></label>
          <label className="field-group"><span>Buscar curso</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Código o nombre" /></label>
        </div>
        <p className="muted-copy">`Elegible`, `ofertado` y `horario compatible` son estados distintos. La fuente no reporta cupos en tiempo real.</p>
      </section>
      <ScheduleEvaluationPanel evaluation={schedule} />
      <div className="offerings-list" aria-live="polite">
        {visibleOfferings.map((offering) => <OfferingCard key={String(offering.id)} offering={offering} selectedSectionIds={selected} onToggleSection={toggleSection} />)}
        {!visibleOfferings.length ? <section className="panel offerings-empty"><h2>No hay oferta registrada para este filtro</h2><p>Que una asignatura no aparezca aquí no demuestra que sea inelegible; puede faltar una fuente temporal o el período seleccionado.</p></section> : null}
      </div>
      <footer className="offerings-footer"><span>La oferta puede cambiar durante inscripción.</span><Link href="/sources">Ver fuentes y procedencia →</Link></footer>
    </div>
  );
}
