"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";

import { problemMessage, signIn } from "@/lib/api";
import { messages } from "@/lib/i18n";
import { safeInternalPath } from "@/lib/url-state";

import { Alert } from "./ui/alert";
import { Button } from "./ui/button";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeInternalPath(searchParams.get("next"));
  const passwordWasReset = searchParams.get("reset") === "success";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCorrelationId(null);
    startTransition(async () => {
      const result = await signIn(email.trim(), password);
      if ("user" in result) {
        router.replace(result.user.must_change_password ? "/change-password" : nextPath);
        router.refresh();
        return;
      }
      setError(
        result.failure.unavailable
          ? messages["es-CO"].loginUnavailable
          : problemMessage(result.failure.problem, messages["es-CO"].loginErrorFallback),
      );
      setCorrelationId(result.failure.correlationId);
    });
  }

  return (
    <form className="auth-form" onSubmit={submit} noValidate>
      {passwordWasReset ? <Alert tone="success">Tu contraseña se actualizó. Ya puedes iniciar sesión.</Alert> : null}
      {error ? (
        <Alert tone="error">
          <p>{error}</p>
          {correlationId ? <small>Correlación: {correlationId}</small> : null}
        </Alert>
      ) : null}
      <div className="field-group">
        <label htmlFor="email">{messages["es-CO"].email}</label>
        <input id="email" name="email" type="email" autoComplete="email" placeholder="nombre@institucion.edu.co" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </div>
      <div className="field-group">
        <div className="field-label-row"><label htmlFor="password">{messages["es-CO"].password}</label><Link href="/reset-password">¿Olvidaste tu contraseña?</Link></div>
        <div className="password-field"><input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /><button className="password-visibility" type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} aria-pressed={showPassword}>{showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}</button></div>
      </div>
      <Button type="submit" wide disabled={isPending || !email || !password}>
        {isPending ? messages["es-CO"].signingIn : messages["es-CO"].submitLogin}
      </Button>
      <p className="auth-security-note"><LockKeyhole size={15} aria-hidden="true" /> Tu sesión y tus datos académicos se protegen mediante acceso institucional.</p>
    </form>
  );
}
