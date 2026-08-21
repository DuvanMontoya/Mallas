import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/require-authenticated-session", () => ({
  requireAuthenticatedSession: vi.fn().mockResolvedValue({
    headers: undefined,
    session: {
      state: "authenticated",
      user: { onboarding_required: false, must_change_password: false, roles: [], student_profile_id: "student" },
    },
  }),
}));

vi.mock("../lib/api", () => ({
  getAcademicOverview: vi.fn().mockResolvedValue({
    data: null,
    failure: { unavailable: true, problem: null, correlationId: null },
  }),
}));

import HomePage from "../app/page";

describe("home dashboard shell", () => {
  it("offers a truthful retry when the private overview is unavailable", async () => {
    render(await HomePage());
    expect(screen.getByRole("heading", { name: /no pudimos cargar tu estado académico/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /reintentar/i })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("link", { name: /malla pública/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /importar historia/i })).not.toBeInTheDocument();
  });
});
