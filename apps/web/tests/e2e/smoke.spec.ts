import { expect, test } from "@playwright/test";

test("student dashboard is reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /tu mapa académico/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /abrir auditoría/i })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toHaveAttribute("href", "#main-content");
});

test("auth shell exposes the real session entry point", async ({ page }) => {
  await page.goto("/login?next=/audit");
  await expect(page.getByRole("heading", { name: /vuelve a tu espacio académico/i })).toBeVisible();
  await expect(page.getByLabel(/correo institucional/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /entrar/i })).toBeDisabled();
});
