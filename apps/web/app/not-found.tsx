import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page-shell module-shell">
      <section className="panel module-panel" role="status">
        <p className="eyebrow accent">404</p>
        <h1>Esta vista no existe</h1>
        <p>La ruta solicitada no está disponible en esta revisión de la plataforma.</p>
        <Link className="button button-primary" href="/">Volver al resumen</Link>
      </section>
    </div>
  );
}
