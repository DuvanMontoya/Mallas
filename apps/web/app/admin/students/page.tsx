import { cookies } from "next/headers";

import { SessionRequired } from "@/components/session-required";
import { StudentAdministrationWorkspace } from "@/components/student-administration-workspace";
import { getAdminEnrollments, getSessionSnapshot, getStudentAdminCatalog } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function StudentAdministrationPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/admin/students" title="Inicia sesión como administrador" description="Las cuentas y matrículas sólo pueden crearse dentro de un alcance administrativo autorizado y auditado." />;
  }
  if (!session.user?.roles.includes("ADMIN")) {
    return <SessionRequired nextPath="/" title="Administración no disponible" description="Tu cuenta no tiene un alcance administrativo activo para gestionar estudiantes." showSignIn={false} />;
  }
  const [catalog, enrollments] = await Promise.all([
    getStudentAdminCatalog({ headers }),
    getAdminEnrollments({ headers }),
  ]);
  if (!catalog.data || !enrollments.data) {
    return <SessionRequired nextPath="/admin/students" title="No pudimos abrir la administración" description={catalog.failure?.problem?.detail ?? enrollments.failure?.problem?.detail ?? "Reintenta cuando la API administrativa esté disponible."} showSignIn={false} />;
  }
  return <StudentAdministrationWorkspace catalog={catalog.data} initialEnrollments={enrollments.data.items} />;
}

