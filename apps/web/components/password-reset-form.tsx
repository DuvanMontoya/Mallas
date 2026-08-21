"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";

import { confirmPasswordReset, problemMessage, requestPasswordReset } from "@/lib/api";

import { Alert } from "./ui/alert";

export function PasswordResetForm({ localDevelopment = false }: { localDevelopment?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid");
  const token = searchParams.get("token");
  const isConfirmation = Boolean(uid && token);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  if (localDevelopment && !isConfirmation) {
    return <div className="local-access-help local-access-help-inline"><p>En una instalación local no se envían correos de recuperación. Rota de forma segura la clave del administrador desde la raíz del proyecto:</p><code>uv run --project apps/api python apps/api/manage.py bootstrap_local_admin --reset-password</code><p>Después consulta <code>var/local-admin-credentials.txt</code> e inicia sesión.</p><Link className="auth-return-link" href="/login">Volver al acceso</Link></div>;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("new_password") ?? "");
    const confirmation = String(form.get("confirmation") ?? "");
    if (isConfirmation && password !== confirmation) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setError(null);
    setMessage(null);
    startTransition(async () => {
      const failure = isConfirmation
        ? await confirmPasswordReset(uid!, token!, password)
        : await requestPasswordReset(email);
      if (failure) {
        setError(problemMessage(failure.problem, "No fue posible procesar la solicitud. Inténtalo de nuevo."));
        return;
      }
      if (isConfirmation) {
        router.replace("/login?reset=success");
        router.refresh();
        return;
      }
      setMessage("Si la cuenta existe, enviamos las instrucciones al correo registrado.");
    });
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      {error ? <Alert tone="error">{error}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      {isConfirmation ? <>
        <label className="field-group"><span>Nueva contraseña</span><input name="new_password" type="password" autoComplete="new-password" required /></label>
        <label className="field-group"><span>Confirmar nueva contraseña</span><input name="confirmation" type="password" autoComplete="new-password" required /></label>
      </> : <label className="field-group"><span>Correo institucional</span><input name="email" type="email" autoComplete="email" required /></label>}
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Procesando…" : isConfirmation ? "Guardar nueva contraseña" : "Enviar instrucciones"}</button>
      <Link className="auth-return-link" href="/login">Volver al acceso</Link>
    </form>
  );
}
