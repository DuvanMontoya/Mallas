import axe from "axe-core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getNotifications: vi.fn(),
  getNotificationPreferences: vi.fn(),
  markNotificationRead: vi.fn(),
  markAllNotificationsRead: vi.fn(),
  updateNotificationPreference: vi.fn(),
}));

vi.mock("../lib/api", () => mocks);

import { NotificationCenter } from "../components/notification-center";

const notification = {
  id: "00000000-0000-4000-8000-000000000901",
  event_id: "00000000-0000-4000-8000-000000000902",
  event_type: "curriculum.revision.published",
  channel: "IN_APP",
  status: "SENT",
  title: "Cambio curricular publicado",
  body: "Se publicó una revisión curricular que puede requerir una revisión de tu cohorte académica.",
  locale: "es-CO",
  link_path: "/audit",
  read_at: null,
  created_at: "2026-08-16T20:00:00Z",
  delivered_at: "2026-08-16T20:00:01Z",
};

const preference = {
  event_type: "curriculum.revision.published",
  in_app_enabled: true,
  email_enabled: false,
  locale: "es-CO",
};

describe("notification center", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getNotifications.mockResolvedValue({ data: { items: [notification], unread_count: 1, next_cursor: null }, failure: null });
    mocks.getNotificationPreferences.mockResolvedValue({ data: { items: [preference] }, failure: null });
    mocks.markNotificationRead.mockResolvedValue({ data: { ...notification, read_at: "2026-08-16T20:01:00Z" }, failure: null });
    mocks.markAllNotificationsRead.mockResolvedValue({ data: { marked_read: 1 }, failure: null });
    mocks.updateNotificationPreference.mockResolvedValue({ data: preference, failure: null });
  });

  it("loads unread items, marks them read, and updates preferences", async () => {
    render(<NotificationCenter enabled />);

    await waitFor(() => expect(screen.getByLabelText(/1 sin leer/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /abrir centro de notificaciones/i }));
    expect(await screen.findByRole("heading", { name: "Notificaciones" })).toBeInTheDocument();
    expect(screen.getByText(notification.body)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /marcar como leída/i }));
    await waitFor(() => expect(mocks.markNotificationRead).toHaveBeenCalledWith(notification.id));
    expect(screen.queryByLabelText(/1 sin leer/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /preferencias/i }));
    expect(screen.getByRole("checkbox", { name: /centro de notificaciones/i })).toBeChecked();
    const emailToggle = screen.getByRole("checkbox", { name: /correo electrónico/i });
    fireEvent.click(emailToggle);
    await waitFor(() => expect(mocks.updateNotificationPreference).toHaveBeenCalledWith(
      preference.event_type,
      { in_app_enabled: true, email_enabled: true, locale: "es-CO" },
    ));
  });

  it("marks the complete feed read and has no serious accessibility violations", async () => {
    const { container } = render(<NotificationCenter enabled />);
    fireEvent.click(await screen.findByRole("button", { name: /abrir centro de notificaciones/i }));
    expect(await screen.findByText(/cambio curricular publicado/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /marcar todo como leído/i }));
    await waitFor(() => expect(mocks.markAllNotificationsRead).toHaveBeenCalledOnce());
    expect((await axe.run(container)).violations).toEqual([]);
  });

  it("moves focus into the dialog and restores it after Escape or close", async () => {
    render(<NotificationCenter enabled />);
    const trigger = await screen.findByRole("button", { name: /abrir centro de notificaciones/i });

    fireEvent.click(trigger);
    const heading = await screen.findByRole("heading", { name: "Notificaciones" });
    expect(document.activeElement).toBe(heading);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.activeElement).toBe(trigger);

    fireEvent.click(trigger);
    await screen.findByRole("heading", { name: "Notificaciones" });
    fireEvent.click(screen.getByRole("button", { name: /cerrar centro de notificaciones/i }));
    expect(document.activeElement).toBe(trigger);
  });
});
