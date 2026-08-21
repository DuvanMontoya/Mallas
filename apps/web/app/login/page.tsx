import type { Metadata } from "next";
import { BookOpenCheck, ChartNetwork, Network, ShieldCheck } from "lucide-react";

import { LoginForm } from "@/components/login-form";
import { messages } from "@/lib/i18n";

export const metadata: Metadata = { title: messages["es-CO"].signIn };

export default function LoginPage() {
  const showLocalSetup = process.env.NODE_ENV !== "production";
  return (
    <div className="auth-workspace">
      <section className="auth-showcase" aria-labelledby="platform-title">
        <p className="eyebrow auth-showcase-eyebrow">Inteligencia curricular</p>
        <h1 id="platform-title">Decisiones académicas con una visión completa.</h1>
        <p>Un espacio de trabajo para comprender el plan, verificar el avance y planear con evidencia.</p>
        <ul className="auth-capabilities" aria-label="Capacidades de la plataforma">
          <li><span className="auth-capability-icon"><BookOpenCheck size={19} aria-hidden="true" /></span><span><strong>Malla navegable</strong><small>Explora estructura, requisitos y evidencia.</small></span></li>
          <li><span className="auth-capability-icon"><Network size={19} aria-hidden="true" /></span><span><strong>Dependencias explicables</strong><small>Entiende qué bloquea y qué abre cada curso.</small></span></li>
          <li><span className="auth-capability-icon"><ChartNetwork size={19} aria-hidden="true" /></span><span><strong>Planeación informada</strong><small>Construye escenarios sin alterar tu historia.</small></span></li>
        </ul>
        <div className="auth-evidence-note"><ShieldCheck size={18} aria-hidden="true" /><span>Las conclusiones académicas se calculan en el servidor y conservan su trazabilidad.</span></div>
      </section>
      <section className="auth-panel panel" aria-labelledby="login-title">
        <p className="eyebrow accent">Acceso seguro</p>
        <h2 id="login-title">{messages["es-CO"].loginTitle}</h2>
        <p className="auth-description">{messages["es-CO"].loginDescription}</p>
        <LoginForm />
        {showLocalSetup ? <details className="local-access-help"><summary>¿Estás preparando esta instalación local?</summary><div><p>No necesitas crear un archivo <code>.env</code> para empezar: el backend usa SQLite local en desarrollo.</p><code>uv run --project apps/api python apps/api/manage.py bootstrap_local_admin</code><p>El comando crea o conserva <code>admin@localhost</code> y guarda sus credenciales sólo en <code>var/local-admin-credentials.txt</code>. Si perdiste ese archivo, ejecuta el mismo comando con <code>--reset-password</code>.</p></div></details> : null}
      </section>
    </div>
  );
}
