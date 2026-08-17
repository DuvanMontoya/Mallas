import { cookies } from "next/headers";

import { PlannerBoard } from "@/components/planner-board";
import { SessionRequired } from "@/components/session-required";
import { getAcademicOverview, getAcademicTerms, getCurriculumMap, getScenarioCompare, getScenarios, getSessionSnapshot } from "@/lib/api";

export const dynamic = "force-dynamic";

type PlannerPageProps = {
  searchParams: Promise<{
    scenario?: string | string[];
    compare?: string | string[];
  }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function PlannerPage({ searchParams }: PlannerPageProps) {
  const params = await searchParams;
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/planner" title="Inicia sesión para planear" description="Los escenarios son privados, versionados y están vinculados a una matrícula concreta." />;
  }
  const isEditorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (isEditorialOnly) {
    return <SessionRequired nextPath="/planner" title="No hay una matrícula disponible" description="Los escenarios pertenecen a una matrícula estudiantil. Esta cuenta administrativa no tiene un espacio de planificación propio." showSignIn={false} />;
  }
  const overviewResult = await getAcademicOverview({ headers });
  const enrollmentId = overviewResult.data?.enrollment.id;
  if (!enrollmentId) {
    return <SessionRequired nextPath="/planner" title="No hay una matrícula disponible" description="El planificador necesita una matrícula activa para mantener escenarios privados y recalcular su auditoría." showSignIn={false} />;
  }

  const [scenariosResult, termsResult, mapResult] = await Promise.all([
    getScenarios({ enrollmentId, headers }),
    getAcademicTerms({ headers }),
    getCurriculumMap({ headers }),
  ]);
  const scenarios = scenariosResult.data?.items ?? [];
  const referencedTermIds = new Set(
    scenarios.flatMap((scenario) => scenario.planned_courses.map((course) => course.term_id)),
  );
  const planningTerms = (termsResult.data?.items ?? []).filter(
    (term) => ["OPEN", "PLANNED"].includes(term.status) || referencedTermIds.has(term.id),
  );
  const selectedId = first(params.scenario) ?? scenarios[0]?.id;
  const compareId = first(params.compare);
  const compareResult = selectedId && compareId
    ? await getScenarioCompare({ leftId: selectedId, rightId: compareId, headers })
    : { data: null, failure: null };

  return (
    <PlannerBoard
      initialScenarios={scenarios}
      initialSelectedId={selectedId}
      initialCompare={compareResult.data}
      terms={planningTerms}
      courseOptions={mapResult.data?.courses ?? []}
      failureMessage={scenariosResult.failure?.problem?.detail ?? undefined}
    />
  );
}
