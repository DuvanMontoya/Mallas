# 23 — Backoffice curricular

## Pantallas

- Source Inbox
- Documents
- Snapshots
- Extraction candidates
- Semantic diff
- Draft revision
- Rule inspector
- Evidence viewer
- Validation results
- Review queue
- Publication
- Revision history
- Impact analysis

## Rule inspector

Debe mostrar AST legible + representación visual + evidencia.

## Diff

Ejemplo:
- `course added`
- `course removed`
- `credits 3 → 4`
- `requirement changed`
- `mandatory → elective`
- `group min 3 → 4`

## Impact analysis

Antes de publicar:
- auditorías afectadas;
- estudiantes cuyo estado podría cambiar;
- reglas desconocidas nuevas;
- ciclos;
- totals inconsistent.

La publicación requiere confirmación explícita.

Después de publicar, el detalle debe conservar la misma vista para auditoría:

- `PublicationEvent` inmutable, revisión nueva y revisión `SUPERSEDED`;
- cursos, agrupaciones y requisitos cambiados, con operación y clave estable;
- matrículas y auditorías históricas afectadas, incluyendo su hash anterior;
- plan de recomputación `degree_audit.recompute` y su requisito de decisión de
  revisión;
- solicitudes de notificación en estado `QUEUED`, sin afirmar que ya fueron
  entregadas.

La ruta de lectura `GET
/api/v1/governance/publications/{publication_id}/impact` expone este recibo a
roles editoriales con alcance institucional/programático. El endpoint no
modifica matrícula, auditoría ni historial. El backoffice debe ofrecer una
corrección como nueva propuesta/revisión y nunca como edición o borrado del
evento anterior.

## Implementación verificable

La pantalla `/sources` reúne la bandeja de fuentes, documentos, snapshots,
propuestas y cola de revisión. El detalle de una propuesta muestra el hash del
snapshot, la revisión candidata, el diff semántico, el AST serializado con
explicación humana, la evidencia, los candidatos extraídos, el informe de
validación, el impacto y la línea de auditoría.

La API de gobernanza está bajo `/api/v1/governance/`:

- `GET inbox`, documentos, snapshots y propuestas para navegación y lectura;
- `submit`, `review` y `publish` para las transiciones controladas;
- revisión individual y `candidates/bulk-preview` + `candidates/bulk-review`;
- vínculo explícito de evidencia por requisito.

Las operaciones de escritura exigen `If-Match` y responden con un conflicto
explicable cuando la versión cambió. La previsualización masiva siempre
devuelve `writes_performed: false` y su token se invalida si cambia la
propuesta o la selección. Un editor puede enviar cambios a revisión, pero el
backend bloquea su autoaprobación; sólo un revisor o administrador con alcance
válido puede aprobar/publicar. Una publicación devuelve un recibo con hashes,
validación, diff, confirmación e impacto post-publicación; la revisión
publicada y el evento asociado no se editan.
