import { cookies } from "next/headers";

import { PlannerBoard } from "@/components/planner-board";
import { getAcademicTerms, getCurriculumMap, getScenarioCompare, getScenarios } from "@/lib/api";

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

  const [scenariosResult, termsResult, mapResult] = await Promise.all([
    getScenarios({ headers }),
    getAcademicTerms({ headers }),
    getCurriculumMap({ headers }),
  ]);
  const scenarios = scenariosResult.data?.items ?? [];
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
      terms={termsResult.data?.items ?? []}
      courseOptions={mapResult.data?.courses ?? []}
      failureMessage={scenariosResult.failure?.problem?.detail ?? undefined}
    />
  );
}
