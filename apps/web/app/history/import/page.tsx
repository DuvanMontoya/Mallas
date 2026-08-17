import { cookies } from "next/headers";

import { HistoryImportWorkspace } from "@/components/history-import-workspace";
import { SessionRequired } from "@/components/session-required";
import {
  getAcademicOverview,
  getCurriculumMap,
  getHistoryImport,
  getSessionSnapshot,
} from "@/lib/api";

export const dynamic = "force-dynamic";

type ImportHistoryPageProps = {
  searchParams: Promise<{ batch?: string | string[] }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function ImportHistoryPage({ searchParams }: ImportHistoryPageProps) {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") {
    return <SessionRequired nextPath="/history/import" title="Inicia sesión antes de importar" description="El archivo, sus candidatos y la reconciliación pertenecen a una matrícula privada." />;
  }
  const overview = await getAcademicOverview({ headers });
  const enrollment = overview.data?.enrollment;
  if (!enrollment) {
    return <SessionRequired nextPath="/history" title="No hay una matrícula disponible" description="La importación exige una matrícula propia o una autorización administrativa auditada." showSignIn={false} />;
  }
  const [map, params] = await Promise.all([
    getCurriculumMap({ enrollmentId: enrollment.id, headers }),
    searchParams,
  ]);
  const batchId = first(params.batch);
  const preview = batchId ? await getHistoryImport(batchId, { headers }) : { data: null, failure: null };
  return (
    <HistoryImportWorkspace
      enrollmentId={enrollment.id}
      initialPreview={preview.data}
      courseOptions={(map.data?.courses ?? []).map((course) => ({ id: course.id, code: course.code, name: course.name }))}
    />
  );
}
