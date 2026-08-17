import { cookies } from "next/headers";

import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { SessionRequired } from "@/components/session-required";
import { getSessionSnapshot, getStudentAnalytics } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalyticsPage() {
  let headers: HeadersInit | undefined;
  try {
    const cookieHeader = (await cookies()).toString();
    headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  } catch {
    headers = undefined;
  }
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/analytics" title="Inicia sesión para consultar tu analítica" description="Las métricas se derivan de tu auditoría privada y no se exponen sin una sesión válida." />;
  }
  const isEditorialOnly = session.user?.roles.some((role) => ["EDITOR", "REVIEWER", "ADMIN"].includes(role)) && !session.user.student_profile_id && !session.user.roles.includes("STUDENT");
  if (isEditorialOnly) {
    return <SessionRequired nextPath="/analytics" title="No hay analítica estudiantil para esta cuenta" description="La analítica personal requiere una matrícula. Las cuentas administrativas sólo acceden a datos mediante superficies institucionales autorizadas." showSignIn={false} />;
  }
  const result = await getStudentAnalytics({ headers });
  return <AnalyticsDashboard analytics={result.data} failure={result.failure} />;
}
