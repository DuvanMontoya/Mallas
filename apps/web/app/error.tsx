"use client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const supportId = error.digest ? `ID ${error.digest}` : "sin identificador";

  return (
    <div className="page-shell" role="alert">
      <section className="panel error-panel">
        <p className="eyebrow">Error recuperable</p>
        <h1>No pudimos cargar esta vista</h1>
        <p>Intenta de nuevo. Si persiste, comparte el identificador de soporte que aparece en los registros.</p>
        <p className="support-id">Identificador: {supportId}</p>
        <button className="button button-primary" type="button" onClick={() => reset()}>
          Reintentar
        </button>
      </section>
    </div>
  );
}
