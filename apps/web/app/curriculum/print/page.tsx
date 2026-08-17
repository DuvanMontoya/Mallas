import { cookies } from "next/headers";

import { CurriculumMapPage } from "@/components/curriculum-map";
import { getCurriculumMap } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CurriculumPrintPage() {
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const result = await getCurriculumMap({ headers });
  return <CurriculumMapPage map={result.data} failureMessage={result.failure?.problem?.detail ?? undefined} printMode />;
}
