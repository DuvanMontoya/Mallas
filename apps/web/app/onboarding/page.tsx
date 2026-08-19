import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { StudentOnboardingForm } from "@/components/student-onboarding-form";
import { getAcademicTerms, getSessionSnapshot, getStudentOnboarding } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OnboardingPage() {
  const cookieHeader = (await cookies()).toString();
  const headers = cookieHeader ? { Cookie: cookieHeader } : undefined;
  const session = await getSessionSnapshot(headers);
  if (session.state !== "authenticated") redirect("/login?next=/onboarding");
  if (session.user?.must_change_password) redirect("/change-password");
  const onboarding = await getStudentOnboarding(headers);
  if (!onboarding.data) redirect("/");
  if (onboarding.data.completed) redirect("/");
  const termResult = await getAcademicTerms({
    headers,
    enrollmentId: onboarding.data.enrollment_id,
  });
  return <StudentOnboardingForm initial={onboarding.data} terms={termResult.data?.items ?? []} />;
}
