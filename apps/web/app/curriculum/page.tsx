import { CurriculumMapPage } from "@/components/curriculum-map";
import { getCurriculumMap } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export const dynamic = "force-dynamic";

export default async function CurriculumPage() {
  const { headers } = await requireAuthenticatedSession("/curriculum");
  const result = await getCurriculumMap({ headers });
  return <CurriculumMapPage map={result.data} failureMessage={result.failure?.problem?.detail ?? undefined} />;
}
