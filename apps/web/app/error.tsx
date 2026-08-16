"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="page-shell" role="alert">
      <section className="panel error-panel">
        <p className="eyebrow">Error recuperable</p>
        <h1>No pudimos cargar esta vista</h1>
        <p>Intenta de nuevo. Si persiste, comparte el identificador de soporte que aparece en los registros.</p>
        <button className="button button-primary" type="button" onClick={() => reset()}>
          Reintentar
        </button>
      </section>
    </main>
  );
}
