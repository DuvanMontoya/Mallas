import { LockKeyhole } from "lucide-react";
import Link from "next/link";

export function SessionRequired({
  nextPath,
  title,
  description,
  showSignIn = true,
}: {
  nextPath: string;
  title: string;
  description: string;
  showSignIn?: boolean;
}) {
  return (
    <div className="page-shell access-page">
      <section className="panel access-panel">
        <LockKeyhole size={24} aria-hidden="true" />
        <p className="eyebrow accent">Espacio privado</p>
        <h1>{title}</h1>
        <p>{description}</p>
        {showSignIn ? <Link className="button button-primary" href={`/login?next=${encodeURIComponent(nextPath)}`}>Iniciar sesión</Link> : null}
        <small>Las herramientas académicas sólo están disponibles dentro de una sesión autenticada.</small>
      </section>
    </div>
  );
}
