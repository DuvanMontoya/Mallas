import { cookies } from "next/headers";

import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { getStudentAnalytics } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage() {
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const result = await getStudentAnalytics({ headers });
  return <AnalyticsDashboard analytics={result.data} failure={result.failure} />;
}
