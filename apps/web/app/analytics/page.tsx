import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { SessionRequired } from "@/components/session-required";
import { getStudentAnalytics } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage() {
  const { headers, session } = await requireAuthenticatedSession("/analytics");
  const isEditorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (isEditorialOnly) {
    return <SessionRequired nextPath="/analytics" title="No hay analítica estudiantil para esta cuenta" description="La analítica personal requiere una matrícula. Las cuentas administrativas sólo acceden a datos mediante superficies institucionales autorizadas." showSignIn={false} />;
  }
  const result = await getStudentAnalytics({ headers });
  return <AnalyticsDashboard analytics={result.data} failure={result.failure} />;
}
