import type { Metadata } from "next";

import { LoginForm } from "@/components/login-form";
import { messages } from "@/lib/i18n";

export const metadata: Metadata = { title: messages["es-CO"].signIn };

export default function LoginPage() {
  return (
    <section className="auth-panel panel" aria-labelledby="login-title">
      <p className="eyebrow accent">Curriculum Navigator</p>
      <h1 id="login-title">{messages["es-CO"].loginTitle}</h1>
      <p className="auth-description">{messages["es-CO"].loginDescription}</p>
      <LoginForm />
    </section>
  );
}
