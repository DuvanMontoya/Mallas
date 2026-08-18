import axe from "axe-core";
import { render, screen } from "@testing-library/react";
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

  it("keeps editorial-only accounts out of private student navigation", () => {
    renderWithProviders(
      <AppShell session={{ state: "authenticated", correlationId: null, user: { id: 7, email: "admin@example.test", email_verified: true, roles: ["ADMIN"], student_profile_id: null, must_change_password: false } }}>
        <div>Gobernanza</div>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: "Fuentes" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Historia" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Planificador" })).not.toBeInTheDocument();
  });

  it("supports legacy student accounts without an explicit STUDENT role", () => {
    renderWithProviders(
      <AppShell session={{ state: "authenticated", correlationId: null, user: { id: 8, email: "student@example.test", email_verified: true, roles: [], student_profile_id: "profile-8", must_change_password: false } }}>
        <div>Malla</div>
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: "Historia" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Planificador" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Fuentes" })).not.toBeInTheDocument();
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
