import axe from "axe-core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LoginForm } from "../components/login-form";
import { PasswordResetForm } from "../components/password-reset-form";
import { requestPasswordReset } from "../lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, requestPasswordReset: vi.fn() };
});

describe("authentication access", () => {
  it("offers accessible credential recovery and password visibility without accessibility violations", async () => {
    const { container } = render(<LoginForm />);

    expect(screen.getByRole("link", { name: /olvidaste tu contraseña/i })).toHaveAttribute("href", "/reset-password");
    const password = screen.getByLabelText("Contraseña");
    expect(password).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(password).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Ocultar contraseña" })).toHaveAttribute("aria-pressed", "true");

    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it("keeps password-reset requests non-enumerating in the interface", async () => {
    vi.mocked(requestPasswordReset).mockResolvedValue(null);
    render(<PasswordResetForm />);

    fireEvent.change(screen.getByLabelText("Correo institucional"), { target: { value: "student@example.test" } });
    fireEvent.submit(screen.getByRole("button", { name: /enviar instrucciones/i }).closest("form")!);

    await waitFor(() => expect(requestPasswordReset).toHaveBeenCalledWith("student@example.test"));
    expect(await screen.findByText(/si la cuenta existe/i)).toBeInTheDocument();
  });
});
