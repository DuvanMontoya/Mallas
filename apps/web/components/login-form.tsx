"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";

import { problemMessage, signIn } from "@/lib/api";
import { messages } from "@/lib/i18n";
import { safeInternalPath } from "@/lib/url-state";

import { Alert } from "./ui/alert";
import { Button } from "./ui/button";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeInternalPath(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
      {error ? (
        <Alert tone="error">
          <p>{error}</p>
          {correlationId ? <small>Correlación: {correlationId}</small> : null}
        </Alert>
      ) : null}
      <div className="field-group">
        <label htmlFor="email">{messages["es-CO"].email}</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
      </div>
      <div className="field-group">
        <label htmlFor="password">{messages["es-CO"].password}</label>
        <input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
      </div>
      <Button type="submit" wide disabled={isPending || !email || !password}>
        {isPending ? messages["es-CO"].signingIn : messages["es-CO"].submitLogin}
      </Button>
    </form>
  );
}
