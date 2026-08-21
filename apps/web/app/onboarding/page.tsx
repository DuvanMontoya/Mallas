import Link from "next/link";
import { redirect } from "next/navigation";

import { StudentOnboardingForm } from "@/components/student-onboarding-form";
import { EmptyState } from "@/components/ui/empty-state";
import { getAcademicTerms, getStudentOnboarding } from "@/lib/api";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export const dynamic = "force-dynamic";

export default async function OnboardingPage() {
  const { headers } = await requireAuthenticatedSession("/onboarding");
  const onboarding = await getStudentOnboarding(headers);
  if (!onboarding.data) {
    if (onboarding.failure?.problem?.status === 404) redirect("/");
    if (onboarding.failure?.problem?.code === "ONBOARDING_NOT_AVAILABLE") {
      return <div className="page-shell"><EmptyState tone="neutral" title="No hay una configuración inicial pendiente" description="Tu cuenta ya no tiene un flujo de configuración inicial que completar. Puedes continuar a tu espacio académico." action={<><Link className="button button-primary" href="/">Ir a mi espacio</Link><Link className="button button-secondary" href="/curriculum">Abrir malla</Link></>} /></div>;
    }
    return <div className="page-shell"><EmptyState tone="unknown" title="No pudimos abrir tu configuración inicial" description={onboarding.failure?.problem?.detail ?? "El servicio de onboarding no está disponible temporalmente."} action={<Link className="button button-primary" href="/onboarding">Reintentar</Link>} /></div>;
  }
  if (onboarding.data.completed) redirect("/");
  const termResult = await getAcademicTerms({
    headers,
    enrollmentId: onboarding.data.enrollment_id,
  });
  const terms = termResult.data?.items ?? [];
  const termsFailure = termResult.failure?.problem?.detail ?? (terms.length === 0 ? "No encontramos períodos académicos válidos para esta matrícula." : null);
  return <StudentOnboardingForm initial={onboarding.data} terms={terms} termsFailure={termsFailure} />;
}
