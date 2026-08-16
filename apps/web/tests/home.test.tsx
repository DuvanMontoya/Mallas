import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("home dashboard shell", () => {
  it("exposes the academic navigation and first-step actions", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /entiende tu siguiente movimiento/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /abrir auditoría/i })).toHaveAttribute("href", "/audit");
    expect(screen.getByRole("link", { name: /carga tu historia/i })).toHaveAttribute("href", "/history/import");
  });
});
