import type { Metadata } from "next";

import { PasswordResetForm } from "@/components/password-reset-form";

export const metadata: Metadata = { title: "Recuperar acceso" };

export default function ResetPasswordPage() {
  const localDevelopment = process.env.NODE_ENV !== "production";
  return (
    <section className="auth-panel panel auth-panel-compact" aria-labelledby="reset-password-title">
      <p className="eyebrow accent">Acceso seguro</p>
      <h1 id="reset-password-title">Recupera o actualiza tu acceso</h1>
      <p className="auth-description">{localDevelopment ? "Recupera de forma segura el acceso de esta instalación local." : "Indica el correo asociado a tu cuenta. Por seguridad, el resultado será el mismo aunque no exista una cuenta registrada."}</p>
      <PasswordResetForm localDevelopment={localDevelopment} />
    </section>
  );
}
