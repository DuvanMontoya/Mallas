import { cookies } from "next/headers";

import { AcademicDashboard } from "@/components/academic-dashboard";
import { getAcademicOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const result = await getAcademicOverview({ headers });

  return (
    <div className="page-shell audit-page-shell">
      <AcademicDashboard overview={result.data} failure={result.failure} />
    </div>
  );
}
