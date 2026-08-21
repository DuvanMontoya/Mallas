import { redirect } from "next/navigation";

import { InitialPasswordForm } from "@/components/initial-password-form";
import { requireAuthenticatedSession } from "@/lib/require-authenticated-session";

export default async function ChangePasswordPage() {
  const { session } = await requireAuthenticatedSession("/change-password");
  if (!session.user?.must_change_password) redirect("/");
  return <section className="auth-panel panel" aria-labelledby="change-password-title"><p className="eyebrow accent">Primer acceso</p><h1 id="change-password-title">Crea tu contraseña privada</h1><p className="auth-description">La clave inicial vence en 72 horas y sólo habilita este cambio. El administrador no conocerá tu nueva contraseña.</p><InitialPasswordForm /></section>;
}
