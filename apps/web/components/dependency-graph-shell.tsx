"use client";

import dynamic from "next/dynamic";

import type { DependencyGraph } from "@/lib/api";

const DependencyGraphExplorer = dynamic(
  () => import("@/components/dependency-graph").then((module) => module.DependencyGraphExplorer),
  {
    ssr: false,
    loading: () => <div className="page-shell"><section className="panel"><p className="eyebrow">Dependencias</p><h1>Cargando proyección del grafo…</h1><p>La vista interactiva se carga de forma diferida para no hidratar el dashboard completo.</p></section></div>,
  },
);

export function DependencyGraphShell({ graph, failureMessage }: { graph: DependencyGraph | null; failureMessage?: string }) {
  return <DependencyGraphExplorer graph={graph} failureMessage={failureMessage} />;
}
