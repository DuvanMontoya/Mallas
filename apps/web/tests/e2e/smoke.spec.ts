import { expect, test } from "@playwright/test";

test("student dashboard is reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /entiende tu siguiente movimiento/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /abrir auditoría/i })).toBeVisible();
});
