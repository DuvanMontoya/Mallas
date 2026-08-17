import axe from "axe-core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DependencyGraphExplorer } from "../components/dependency-graph";
import type { DependencyGraph } from "../lib/api";
import fixture from "./e2e/fixtures/dependency-graph.json";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("../components/dependency-graph-canvas", () => ({
  DependencyGraphCanvas: ({ nodes, edges }: { nodes: unknown[]; edges: unknown[] }) => (
    <div aria-label="Grafo visual de dependencias" data-testid="dependency-graph-canvas">
      {nodes.length} nodos · {edges.length} relaciones
    </div>
  ),
}));

describe("dependency graph explorer", () => {
  beforeEach(() => window.localStorage.clear());

  it("keeps condition nodes, direct relations and a readable textual alternative", async () => {
    const { container } = render(<DependencyGraphExplorer graph={fixture as DependencyGraph} />);

    expect(screen.getByRole("heading", { name: /entiende qué desbloquea/i })).toBeInTheDocument();
    expect(screen.getByText(/todas las condiciones/i)).toBeInTheDocument();
    expect(screen.getByText(/lista textual de relaciones/i)).toBeInTheDocument();
    expect(screen.getByText(/1000003 abre una ruta hacia 2000001/i)).toBeInTheDocument();
    expect(screen.getByText(/sin modificar reglas/i)).toBeInTheDocument();
    expect((await axe.run(container)).violations).toEqual([]);
  });

  it("filters semantic nodes and keeps focus navigation explicit", () => {
    render(<DependencyGraphExplorer graph={fixture as DependencyGraph} />);

    fireEvent.change(screen.getByLabelText("Tipo de nodo"), { target: { value: "CONDITION" } });
    expect(screen.getByTestId("dependency-graph-canvas")).toHaveTextContent("2 nodos");
    expect(screen.getByText("Todas las condiciones")).toBeInTheDocument();
    expect(screen.getByText("Umbral de créditos en agrupación")).toBeInTheDocument();
    expect(screen.getByText(/tipo ALL/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Buscar curso o condición"), { target: { value: "no-existe" } });
    expect(screen.getAllByText(/ningún nodo coincide/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ajusta o restablece los filtros/i).length).toBeGreaterThan(0);
  });
});
