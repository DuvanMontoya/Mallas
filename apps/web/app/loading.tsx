export default function Loading() {
  return (
    <div className="page-shell" aria-busy="true" aria-live="polite" role="status">
      <div className="loading-card">
        <span className="loading-mark" aria-hidden="true" />
        <p className="eyebrow">Espacio académico</p>
        <p>Cargando tu espacio académico…</p>
      </div>
    </div>
  );
}
