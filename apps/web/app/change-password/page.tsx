import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { InitialPasswordForm } from "@/components/initial-password-form";
import { getSessionSnapshot } from "@/lib/api";

export default async function ChangePasswordPage() {
  const cookieHeader = (await cookies()).toString();
  const session = await getSessionSnapshot(cookieHeader ? { Cookie: cookieHeader } : undefined);
  if (session.state !== "authenticated") redirect("/login?next=/change-password");
  if (!session.user?.must_change_password) redirect("/");
  return <section className="auth-panel panel" aria-labelledby="change-password-title"><p className="eyebrow accent">Primer acceso</p><h1 id="change-password-title">Crea tu contraseña privada</h1><p className="auth-description">La clave inicial vence en 72 horas y sólo habilita este cambio. El administrador no conocerá tu nueva contraseña.</p><InitialPasswordForm /></section>;
}
