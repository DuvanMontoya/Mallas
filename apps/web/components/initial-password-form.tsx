"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";

import { changeInitialPassword, problemMessage } from "@/lib/api";

import { Alert } from "./ui/alert";

export function InitialPasswordForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const currentPassword = String(form.get("current_password") ?? "");
    const newPassword = String(form.get("new_password") ?? "");
    const confirmation = String(form.get("confirmation") ?? "");
    if (newPassword !== confirmation) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setError(null);
    startTransition(async () => {
      const failure = await changeInitialPassword(currentPassword, newPassword);
      if (failure) {
        setError(problemMessage(failure.problem, "No fue posible cambiar la contraseña."));
        return;
      }
      router.replace("/");
      router.refresh();
    });
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      {error ? <Alert tone="error">{error}</Alert> : null}
      <label className="field-group"><span>Contraseña inicial</span><input name="current_password" type="password" autoComplete="current-password" required /></label>
      <label className="field-group"><span>Nueva contraseña</span><input name="new_password" type="password" autoComplete="new-password" minLength={12} required /></label>
      <label className="field-group"><span>Confirmar nueva contraseña</span><input name="confirmation" type="password" autoComplete="new-password" minLength={12} required /></label>
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Guardando…" : "Guardar y continuar"}</button>
    </form>
  );
}
