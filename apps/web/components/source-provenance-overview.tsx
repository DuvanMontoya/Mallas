import { Archive, ExternalLink, Fingerprint } from "lucide-react";
import Link from "next/link";

import type { CurriculumMap } from "@/lib/api";

import { Alert } from "./ui/alert";
import { StatusBadge } from "./ui/status-badge";

export function SourceProvenanceOverview({ map, showEditorialAccess = false }: { map: CurriculumMap; showEditorialAccess?: boolean }) {
  const evidence = new Map<string, CurriculumMap["courses"][number]["source_evidence"][number]>();
  for (const course of map.courses) {
    for (const item of course.source_evidence) evidence.set(item.reference, item);
    for (const requirement of course.requirements) {
      for (const item of requirement.evidence) evidence.set(item.reference, item);
    }
  }
  const rows = [...evidence.values()].sort((left, right) => (left.page ?? 0) - (right.page ?? 0) || left.locator.localeCompare(right.locator)).slice(0, 80);
  return (
    <div className="sources-public-page">
      <section className="panel sources-public-hero">
        <div>
          <p className="eyebrow accent">Procedencia pública</p>
          <h1>La malla puede explicar de dónde sale cada regla.</h1>
          <p>Esta vista no es un backoffice. Resume la revisión publicada, su huella y los fragmentos archivados que respaldan cursos y requisitos.</p>
        </div>
        <div className="sources-public-status"><StatusBadge tone={map.revision.status === "PUBLISHED" ? "passed" : "unknown"} label={map.revision.status === "PUBLISHED" ? "Revisión publicada" : map.revision.status} /><span>Vigente desde {map.revision.effective_from}</span></div>
      </section>
      <section className="sources-public-facts" aria-label="Identidad de la revisión">
        <article><Archive size={18} aria-hidden="true" /><span>Revisión</span><strong>{map.revision.revision_code}</strong><small>{map.revision.plan_title}</small></article>
        <article><Fingerprint size={18} aria-hidden="true" /><span>Huella de contenido</span><code>{map.revision.content_hash}</code><small>{map.courses.length} asignaturas · {map.revision.total_required_credits} créditos</small></article>
        <article><span>Estado del layout</span><strong>No normativo</strong><small>La ubicación visual no crea prerrequisitos ni semestres oficiales.</small></article>
      </section>
      {map.revision.source_note ? <Alert tone="info">{map.revision.source_note}</Alert> : null}
      <section className="panel sources-evidence-ledger" aria-labelledby="sources-evidence-title">
        <div className="section-heading"><div><p className="eyebrow">Archivo verificable</p><h2 id="sources-evidence-title">Fragmentos de evidencia</h2></div><span className="tag tag-outline">Mostrando {rows.length} de {evidence.size}</span></div>
        <ol>{rows.map((item) => <li key={item.reference}><span className="sources-locator">{item.locator}</span><div><strong>{item.source_title}</strong><p>{item.excerpt || item.annotation || "El snapshot conserva el locator sin transcripción pública."}</p><small>SHA-256 {item.snapshot_sha256.slice(0, 20)}…{item.page ? ` · página ${item.page}` : ""}</small></div>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer" aria-label={`Abrir fuente de ${item.locator}`}><ExternalLink size={15} aria-hidden="true" /></a> : null}</li>)}</ol>
      </section>
      <div className="sources-public-actions"><Link className="button button-primary" href="/curriculum">Volver a la malla</Link>{showEditorialAccess ? <Link className="button button-secondary" href="/login?next=%2Fsources">Acceso editorial</Link> : null}</div>
    </div>
  );
}
