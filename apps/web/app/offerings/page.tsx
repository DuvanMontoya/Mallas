import { cookies } from "next/headers";

import { OfferingsExplorer } from "@/components/offerings-explorer";
import { getOfferingSchedule, getOfferings } from "@/lib/api";

export const dynamic = "force-dynamic";

type OfferingsPageProps = {
  searchParams: Promise<{
    term?: string | string[];
    course?: string | string[];
    enrollment?: string | string[];
    sections?: string | string[];
  }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function OfferingsPage({ searchParams }: OfferingsPageProps) {
  const params = await searchParams;
  const termCode = first(params.term);
  const courseCode = first(params.course);
  const enrollmentId = first(params.enrollment);
  const sectionIds = (first(params.sections) ?? "").split(",").map((value) => value.trim()).filter(Boolean);
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const result = await getOfferings({ termCode, courseCode, enrollmentId, headers });
  const scheduleResult = termCode && sectionIds.length
    ? await getOfferingSchedule({ termCode, sectionIds, headers })
    : { data: null, failure: null };
  return (
    <OfferingsExplorer
      data={result.data}
      schedule={scheduleResult.data}
      selectedSectionIds={sectionIds}
      failureMessage={result.failure?.problem?.detail ?? undefined}
    />
  );
}
