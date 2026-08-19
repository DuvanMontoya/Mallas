import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PersonProfileForm } from "@/components/person-profile-form";

const { updatePersonProfile, exportPersonProfile } = vi.hoisted(() => ({
  updatePersonProfile: vi.fn(),
  exportPersonProfile: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, updatePersonProfile, exportPersonProfile };
});

const profile = {
  email: "estudiante@unal.edu.co",
  first_name: "Ana",
  middle_names: "María",
  first_surname: "Pérez",
  second_surname: "Ruiz",
  preferred_name: "Ani",
  birth_date: "2004-02-20",
  age: 22,
  data_status: "CONFIRMED",
  verification_method: "SELF_DECLARED",
  version: "2026-08-19T03:00:00+00:00",
};

describe("PersonProfileForm", () => {
  beforeEach(() => {
    updatePersonProfile.mockReset();
    exportPersonProfile.mockReset();
  });

  it("updates only the authenticated person's structured identity with its version", async () => {
    updatePersonProfile.mockResolvedValue({ data: { ...profile, first_name: "Ana Sofía", version: "new" }, failure: null });
    render(<PersonProfileForm initialProfile={profile} />);
    fireEvent.change(screen.getByLabelText("Primer nombre"), { target: { value: "Ana Sofía" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(updatePersonProfile).toHaveBeenCalledWith(expect.objectContaining({
      first_name: "Ana Sofía",
      first_surname: "Pérez",
      birth_date: "2004-02-20",
    }), profile.version));
    expect(await screen.findByRole("status")).toHaveTextContent("actualizados y auditados");
  });

  it("explains that deletion requires an institutional retention review", () => {
    render(<PersonProfileForm initialProfile={profile} />);
    expect(screen.getByText(/supresión de una cuenta activa requiere revisión institucional/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar datos de identidad" })).toBeInTheDocument();
  });
});
