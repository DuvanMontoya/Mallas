import { AcademicDashboard } from "@/components/academic-dashboard";
import { getAcademicOverview } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const { headers } = await requireAuthenticatedSession("/audit");
  const result = await getAcademicOverview({ headers });

  return (
    <div className="page-shell audit-page-shell">
      <AcademicDashboard overview={result.data} failure={result.failure} />
    </div>
  );
}
