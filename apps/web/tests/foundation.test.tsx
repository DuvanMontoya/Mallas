import axe from "axe-core";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "../components/app-shell";
import { ThemeProvider } from "../components/theme-provider";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

describe("product shell", () => {
  it("exposes keyboard-navigable primary navigation and an explicit connection state", () => {
    const { getByRole, getAllByRole } = renderShell();

    expect(getByRole("link", { name: /curriculum navigator/i })).toHaveAttribute("href", "/");
    expect(getByRole("link", { name: "Resumen" })).toHaveAttribute("aria-current", "page");
    expect(getAllByRole("navigation").length).toBeGreaterThanOrEqual(1);
    expect(getByRole("status")).toHaveTextContent(/api no disponible/i);
  });

  it("has no serious automated accessibility violations in the base shell", async () => {
    const { container } = renderShell();
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});

function renderShell() {
  return renderWithProviders(
    <AppShell session={{ state: "unavailable", user: null, correlationId: null }}>
      <div>Contenido de prueba</div>
    </AppShell>,
  );
}

function renderWithProviders(ui: ReactNode) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}
