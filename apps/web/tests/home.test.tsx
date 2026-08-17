import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("home dashboard shell", () => {
  it("offers a truthful retry when the private overview is unavailable", async () => {
    render(await HomePage());
    expect(screen.getByRole("heading", { name: /no pudimos cargar tu estado académico/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /reintentar/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /ver malla pública/i })).toHaveAttribute("href", "/curriculum");
    expect(screen.queryByRole("link", { name: /importar historia/i })).not.toBeInTheDocument();
  });
});
