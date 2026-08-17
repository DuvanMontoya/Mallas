import { cookies } from "next/headers";

import { HistoryWorkspace } from "@/components/history-workspace";
import { SessionRequired } from "@/components/session-required";
import { getAcademicOverview, getAcademicTerms, getCurriculumMap, getHistoryAttempts, getSessionSnapshot } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/history" title="Inicia sesión para consultar tu historia" description="Los intentos, notas y reconocimientos sólo son visibles para su propietario o un rol autorizado." />;
  }
  const overview = await getAcademicOverview({ headers });
  const enrollment = overview.data?.enrollment;
  if (!enrollment) {
    return <SessionRequired nextPath="/history" title="No hay una matrícula seleccionada" description="Esta cuenta no tiene una matrícula propia disponible. El acceso administrativo a otra persona requiere un flujo explícito y auditado." showSignIn={false} />;
  }
  const [firstAttempts, mapResult, termsResult] = await Promise.all([
    getHistoryAttempts({ enrollmentId: enrollment.id, limit: 100, sort: "term", headers }),
    getCurriculumMap({ enrollmentId: enrollment.id, headers }),
    getAcademicTerms({ enrollmentId: enrollment.id, headers }),
  ]);
  if (!firstAttempts.data) {
    return <SessionRequired nextPath="/history" title="No fue posible abrir la historia" description={firstAttempts.failure?.problem?.detail ?? "La API no devolvió un registro académico verificable."} showSignIn={false} />;
  }
  const attemptsPage = { ...firstAttempts.data, items: [...firstAttempts.data.items] };
  let nextCursor = firstAttempts.data.next_cursor;
  while (nextCursor && attemptsPage.items.length < attemptsPage.total) {
    const nextPage = await getHistoryAttempts({ enrollmentId: enrollment.id, limit: 100, cursor: nextCursor, sort: "term", headers });
    if (!nextPage.data) {
      return <SessionRequired nextPath="/history" title="La historia quedó incompleta" description="No fue posible recuperar todas las páginas del registro académico. Reintenta antes de tomar decisiones con estos datos." showSignIn={false} />;
    }
    attemptsPage.items.push(...nextPage.data.items);
    nextCursor = nextPage.data.next_cursor;
  }
  attemptsPage.limit = attemptsPage.items.length;
  attemptsPage.next_offset = null;
  attemptsPage.next_cursor = null;
  return <HistoryWorkspace enrollmentId={enrollment.id} studentName={enrollment.student_name} attemptsPage={attemptsPage} courseOptions={(mapResult.data?.courses ?? []).map((course) => ({ code: course.code, name: course.name }))} termOptions={(termsResult.data?.items ?? []).map((term) => term.code)} />;
}
