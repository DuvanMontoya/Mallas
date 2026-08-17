import { expect, test } from "@playwright/test";

test("student dashboard is reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /tu mapa académico/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Abrir auditoría", exact: true })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toHaveAttribute("href", "#main-content");
});

test("notification center exposes unread state, read actions, and preferences", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel(/1 sin leer/i)).toBeVisible();
  await page.getByRole("button", { name: /abrir centro de notificaciones/i }).click();
  await expect(page.getByRole("heading", { name: "Notificaciones" })).toBeVisible();
  await expect(page.getByText(/se publicó una revisión curricular/i)).toBeVisible();
  await page.getByRole("button", { name: /preferencias/i }).click();
  await expect(page.getByRole("checkbox", { name: /correo electrónico/i })).toBeVisible();
  await page.getByRole("button", { name: /marcar todo como leído/i }).click();
  await expect(page.getByLabel(/1 sin leer/i)).toHaveCount(0);
});

test("auth shell exposes the real session entry point", async ({ page }) => {
  await page.goto("/login?next=/audit");
  await expect(page.getByRole("heading", { name: /vuelve a tu espacio académico/i })).toBeVisible();
  await expect(page.getByLabel(/correo institucional/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /entrar/i })).toBeDisabled();
});

test("editorial backoffice shows source provenance, semantic diff, and rule inspector", async ({ page }) => {
  await page.goto("/sources");
  await expect(page.getByRole("heading", { name: /gobierna antes de publicar/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /revisión editorial de prueba/i })).toBeVisible();
  await expect(page.getByText(/semantic diff/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: /ast legible/i })).toBeVisible();
  await expect(page.getByText(/haber aprobado el curso stat000/i)).toBeVisible();
  await page.getByRole("button", { name: /enviar a revisión/i }).click();
  await expect(page.getByText("IN_REVIEW").first()).toBeVisible();
  await page.getByRole("textbox", { name: /comentario de revisión/i }).fill("Evidencia y diff revisados por el revisor de la cohorte.");
  await page.getByRole("button", { name: /aprobar revisión/i }).click();
  await expect(page.getByText("APPROVED").first()).toBeVisible();
  await page.getByRole("textbox", { name: /confirmación explícita de publicación/i }).fill("He revisado el diff, la validación, el impacto y la evidencia.");
  await page.getByRole("button", { name: /publicar revisión aprobada/i }).click();
  await expect(page.getByText("PUBLISHED").first()).toBeVisible();
  await expect(page.getByText(/recibo de publicación/i)).toBeVisible();
});

test("student fixture explains incomplete audit without calling credits graduation", async ({ page }) => {
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: /tu avance real/i })).toBeVisible();
  await expect(page.getByLabel("Créditos de la auditoría").locator("article").first().locator("strong")).toHaveText("7/141");
  await expect(page.getByText(/4% de créditos aplicados/i)).toBeVisible();
  await expect(page.getByText(/por verificar · graduation:foreign_language_b1/i)).toBeVisible();
  await expect(page.getByText(/este porcentaje sólo describe créditos aplicados/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /abrir curso y requisitos/i }).first()).toHaveAttribute(
    "href",
    "/curriculum?selected=1000003",
  );
  const evidence = page.locator("details.evidence-popover").last();
  await evidence.locator("summary").click();
  await expect(evidence).toHaveAttribute("open", "");
  await expect(evidence.getByText(/reglamento de prueba fixture/i)).toBeVisible();
});

test("analytics page shows source-backed student metrics and definitions", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: /tu avance, explicado sin cajas negras/i })).toBeVisible();
  await expect(page.getByText("64 / 141")).toHaveCount(0);
  await expect(page.locator(".analytics-metric").filter({ hasText: "Créditos aplicados" }).getByText("7 / 141")).toBeVisible();
  await expect(page.getByText("2000001", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /qué significa cada métrica/i })).toBeVisible();
});

test("curriculum map separates visual layout from official curriculum and opens course detail", async ({ page }) => {
  await page.goto("/curriculum");
  await expect(page.getByRole("heading", { name: /explora el plan/i })).toBeVisible();
  await expect(page.getByText(/las columnas derivadas no son semestres oficiales/i)).toBeVisible();
  await expect(page.locator("#curriculum-layout")).toHaveValue("dependency-depth");
  await expect(page.getByRole("link", { name: "Vista para imprimir", exact: true })).toHaveAttribute("href", /\/curriculum\/print/);
  await page.getByRole("button", { name: /1000003.*álgebra lineal/i }).click();
  await expect(page).toHaveURL(/selected=1000003/);
  await expect(page.getByRole("heading", { name: "Álgebra lineal", level: 2 })).toBeVisible();
  await expect(page.getByText(/requisitos para cursarla/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /cerrar ficha de asignatura/i })).toBeVisible();
});

test("dependency graph preserves semantic conditions and its textual alternative", async ({ page }) => {
  await page.goto("/graph?selected=1000003");
  await expect(page.getByRole("heading", { name: /entiende qué desbloquea/i })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/lista textual de relaciones/i)).toBeVisible();
  await expect(page.getByText(/condición: all, any, umbral/i)).toBeVisible();
  await expect(page.getByText(/los nodos no se pueden arrastrar/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "1000003" })).toBeVisible();
  await expect(page.getByRole("button", { name: /abrir análisis de 1000003/i })).toBeVisible();
  await expect(page.getByText(/2000001 · modelos estadísticos/i)).toBeVisible();
});

test("offerings separates academic state, source freshness, capacity and schedule conflicts", async ({ page }) => {
  await page.goto("/offerings?term=2026-2S");
  await expect(page.getByRole("heading", { name: /encuentra grupos sin confundir/i })).toBeVisible();
  await expect(page.getByText(/fuente fresca/i).first()).toBeVisible();
  await expect(page.getByText(/académico: eligible/i)).toBeVisible();
  await expect(page.getByText(/académico: blocked/i)).toBeVisible();
  await expect(page.getByText(/dato no reportado/i).first()).toBeVisible();
  const first = page.getByRole("checkbox", { name: /seleccionar grupo 1 de 2016377/i });
  const second = page.getByRole("checkbox", { name: /seleccionar grupo 1 de 2016379/i });
  await first.check();
  await second.check();
  await expect(page).toHaveURL(/sections=/);
  await expect(page.getByRole("heading", { name: /hay solapamientos/i })).toBeVisible();
  await expect(page.getByText(/se solapan/i)).toBeVisible();
});

test("planner keeps scenarios private and exposes an accessible movement alternative", async ({ page }) => {
  await page.goto("/planner");
  await expect(page.getByRole("heading", { name: /planea sin alterar tu historia real/i })).toBeVisible();
  await expect(page.getByText(/privado por defecto/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "2026-2S" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "2027-1S" })).toBeVisible();
  await page.getByRole("button", { name: /optimizar ruta/i }).click();
  await expect(page.getByText("OPTIMAL").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /comparación contra el escenario actual/i })).toBeVisible();

  const move = page.getByRole("combobox", { name: /mover 1000003 a otro período/i });
  const currentTerm = await move.inputValue();
  const destinationTerm = currentTerm === "00000000-0000-4000-8000-000000000401"
    ? "00000000-0000-4000-8000-000000000402"
    : "00000000-0000-4000-8000-000000000401";
  await move.selectOption(destinationTerm);
  await expect(move).toHaveValue(destinationTerm);
  await expect(page.getByRole("button", { name: /bloquear 1000003/i })).toBeVisible();

  await page.getByRole("button", { name: /duplicar/i }).click();
  await expect(page.getByRole("combobox", { name: /escenario activo/i })).toContainText("copia");
  await page.getByRole("combobox", { name: /comparar con/i }).selectOption("00000000-0000-4000-8000-000000000501");
  await expect(page.getByRole("heading", { name: /se mantienen/i })).toBeVisible();
});
