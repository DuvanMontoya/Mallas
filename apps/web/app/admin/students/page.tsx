import Link from "next/link";

import { SessionRequired } from "@/components/session-required";
import { StudentAdministrationWorkspace } from "@/components/student-administration-workspace";
import { EmptyState } from "@/components/ui/empty-state";
import { getAdminEnrollments, getStudentAdminCatalog } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export const dynamic = "force-dynamic";

export default async function StudentAdministrationPage() {
  const { headers, session } = await requireAuthenticatedSession("/admin/students");
  if (!session.user?.roles.includes("ADMIN")) {
    return <SessionRequired nextPath="/" title="Administración no disponible" description="Tu cuenta no tiene un alcance administrativo activo para gestionar estudiantes." showSignIn={false} />;
  }
  const [catalog, enrollments] = await Promise.all([
    getStudentAdminCatalog({ headers }),
    getAdminEnrollments({ headers }),
  ]);
  if (!catalog.data || !enrollments.data) {
    return <div className="page-shell"><EmptyState tone="unknown" title="No pudimos abrir la administración" description={catalog.failure?.problem?.detail ?? enrollments.failure?.problem?.detail ?? "La API administrativa no está disponible temporalmente."} action={<><Link className="button button-primary" href="/admin/students">Reintentar</Link><Link className="button button-secondary" href="/curriculum">Abrir malla</Link></>} /></div>;
  }
  return <StudentAdministrationWorkspace catalog={catalog.data} initialPage={enrollments.data} currentUserId={session.user.id} />;
}
