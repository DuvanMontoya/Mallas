import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("home dashboard shell", () => {
  it("exposes the academic navigation and first-step actions", async () => {
    render(await HomePage());
    expect(screen.getByRole("heading", { name: /tu mapa académico/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /abrir auditoría/i })).toHaveAttribute("href", "/audit");
    expect(screen.getByRole("link", { name: /carga tu historia/i })).toHaveAttribute("href", "/history/import");
  });
});
