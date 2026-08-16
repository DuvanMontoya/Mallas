import Link from "next/link";

export function ModuleLanding({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <main className="page-shell module-shell">
      <Link className="text-link" href="/">← Volver al resumen</Link>
      <section className="panel module-panel">
        <p className="eyebrow accent">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
        <Link className="button button-primary" href="/">Continuar en el inicio</Link>
      </section>
    </main>
  );
}
