import { cookies } from "next/headers";

import { HistoryWorkspace } from "@/components/history-workspace";
import { SessionRequired } from "@/components/session-required";
import { getAcademicTerms, getCurriculumMap, getHistoryAttempts, getHistoryContext, getSessionSnapshot } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/history" title="Inicia sesión para consultar tu historia" description="Los intentos, notas y reconocimientos sólo son visibles para su propietario o un rol autorizado." />;
  }
  const context = await getHistoryContext({ headers });
  if (!context.data) {
    return <SessionRequired nextPath="/history" title="No hay una matrícula seleccionada" description="Esta cuenta no tiene una matrícula propia disponible. El acceso administrativo a otra persona requiere un flujo explícito y auditado." showSignIn={false} />;
  }
  const enrollmentId = context.data.enrollment_id;
  const [firstAttempts, mapResult, termsResult] = await Promise.all([
    getHistoryAttempts({ enrollmentId, limit: 100, sort: "term", headers }),
    getCurriculumMap({ enrollmentId, headers }),
    getAcademicTerms({ enrollmentId, headers }),
  ]);
  if (!firstAttempts.data) {
    return <SessionRequired nextPath="/history" title="No fue posible abrir la historia" description={firstAttempts.failure?.problem?.detail ?? "La API no devolvió un registro académico verificable."} showSignIn={false} />;
  }
  const attemptsPage = { ...firstAttempts.data, items: [...firstAttempts.data.items] };
  let nextCursor = firstAttempts.data.next_cursor;
  while (nextCursor && attemptsPage.items.length < attemptsPage.total) {
    const nextPage = await getHistoryAttempts({ enrollmentId, limit: 100, cursor: nextCursor, sort: "term", headers });
    if (!nextPage.data) {
      return <SessionRequired nextPath="/history" title="La historia quedó incompleta" description="No fue posible recuperar todas las páginas del registro académico. Reintenta antes de tomar decisiones con estos datos." showSignIn={false} />;
    }
    attemptsPage.items.push(...nextPage.data.items);
    nextCursor = nextPage.data.next_cursor;
  }
  if (attemptsPage.items.length !== attemptsPage.total) {
    return <SessionRequired nextPath="/history" title="La historia cambió durante la consulta" description="El registro académico se actualizó mientras se cargaba. Reintenta para trabajar con una versión completa y coherente." showSignIn={false} />;
  }
  attemptsPage.limit = attemptsPage.items.length;
  attemptsPage.next_offset = null;
  attemptsPage.next_cursor = null;
  return <HistoryWorkspace enrollmentId={enrollmentId} studentName={context.data.student_name} attemptsPage={attemptsPage} courseOptions={(mapResult.data?.courses ?? []).map((course) => ({ code: course.code, name: course.name }))} termOptions={(termsResult.data?.items ?? []).map((term) => term.code)} reviewPending={context.data.status === "NEEDS_REVIEW"} />;
}
