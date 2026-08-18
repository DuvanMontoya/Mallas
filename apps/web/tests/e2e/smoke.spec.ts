import { expect, test } from "@playwright/test";

test("student dashboard is reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Mi carrera" })).toBeVisible();
  await expect(page.getByRole("link", { name: /ver mi malla/i })).toBeVisible();
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
  await expect(page.getByRole("heading", { name: /revisiones curriculares/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /revisión editorial de prueba/i })).toBeVisible();
  await expect(page.getByText(/diff semántico/i)).toBeVisible();
  await page.getByText("Inspeccionar reglas y evidencia", { exact: true }).click();
  await expect(page.getByRole("heading", { name: /qué significa la regla y de dónde sale/i })).toBeVisible();
  await expect(page.getByText(/haber aprobado el curso stat000/i)).toBeVisible();
  await page.getByRole("button", { name: /enviar a revisión/i }).click();
  const reviewComment = page.getByRole("textbox", { name: /comentario de revisión/i });
  await expect(reviewComment).toBeVisible();
  await reviewComment.fill("Evidencia y diff revisados por el revisor de la cohorte.");
  await page.getByRole("button", { name: /aprobar revisión/i }).click();
  const publicationConfirmation = page.getByRole("textbox", { name: /confirmación explícita de publicación/i });
  await expect(publicationConfirmation).toBeVisible();
  await publicationConfirmation.fill("He revisado el diff, la validación, el impacto y la evidencia.");
  await page.getByRole("button", { name: /publicar revisión aprobada/i }).click();
  await expect(page.getByText(/recibo de publicación/i)).toBeVisible();
});

test("student fixture explains incomplete audit without calling credits graduation", async ({ page }) => {
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: /créditos por completar/i })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Créditos aplicados" })).toHaveAttribute("aria-valuenow", "7");
  await expect(page.getByRole("progressbar", { name: "Créditos aplicados" })).toHaveAttribute("aria-valuemax", "141");
  await expect(page.getByRole("link", { name: /1000003 álgebra lineal/i })).toHaveAttribute("href", "/curriculum?selected=1000003");
  await page.getByText("Entender bloqueos y requisitos", { exact: true }).click();
  await expect(page.getByRole("heading", { name: /requisitos externos y evidencia/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "GRADUATION:FOREIGN_LANGUAGE_B1" })).toBeVisible();
  await page.getByText("Cómo se calculó este resultado", { exact: true }).click();
  await expect(page.getByText(/aprobar créditos no certifica por sí solo el grado/i)).toBeVisible();
});

test("analytics page shows source-backed student metrics and definitions", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: /evolución académica/i })).toBeVisible();
  await expect(page.getByText("64 / 141")).toHaveCount(0);
  await expect(page.locator(".analytics-metric").filter({ hasText: "Créditos aplicados" }).getByText("7 / 141")).toBeVisible();
  await expect(page.getByText("2000001", { exact: true })).toBeVisible();
  await page.getByText("Cómo se calculan estas métricas", { exact: true }).click();
  await expect(page.getByRole("heading", { name: /qué significa cada métrica/i })).toBeVisible();
});

test("curriculum map separates visual layout from official curriculum and opens course detail", async ({ page }) => {
  await page.goto("/curriculum");
  await expect(page.getByRole("heading", { name: /malla curricular/i })).toBeVisible();
  await page.getByText("Explorar y filtrar el plan completo", { exact: true }).click();
  await expect(page.getByRole("option", { name: /no normativo/i }).first()).toBeAttached();
  await expect(page.locator("#curriculum-layout")).toHaveValue("dependency-depth");
  await expect(page.getByRole("link", { name: "Vista de impresión", exact: true })).toHaveAttribute("href", /\/curriculum\/print/);
  await page.getByRole("button", { name: /1000003.*álgebra lineal/i }).first().click();
  await expect(page).toHaveURL(/selected=1000003/);
  await expect(page.getByRole("heading", { name: "Álgebra lineal", level: 2 })).toBeVisible();
  await expect(page.getByText(/requisitos para cursarla/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /cerrar ficha de asignatura/i })).toBeVisible();
});

test("dependency graph preserves semantic conditions and its textual alternative", async ({ page }) => {
  await page.goto("/graph?selected=1000003");
  await expect(page.getByRole("heading", { name: "1000003", level: 1 })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/distribución visual no normativa/i)).toBeVisible();
  await page.getByText("Alternativa textual accesible", { exact: true }).click();
  await expect(page.getByText(/lista textual de relaciones/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "1000003", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: /abrir análisis de 1000003/i })).toBeVisible();
  await expect(page.getByTestId("graph-textual-course-2000001")).toContainText("Modelos estadísticos");
});

test("offerings separates academic state, source freshness, capacity and schedule conflicts", async ({ page }) => {
  await page.goto("/offerings?term=2026-2S");
  await expect(page.getByRole("heading", { name: "2026-2S", level: 1 })).toBeVisible();
  await expect(page.getByText(/fuente fresca/i).first()).toBeVisible();
  await expect(page.getByLabel(/estados de 2016377/i)).toContainText("Elegibilidad: Puedes cursarla");
  await expect(page.getByLabel(/estados de 2016379/i)).toContainText("Elegibilidad: Prerrequisitos pendientes");
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
  await expect(page.getByRole("heading", { name: /ruta equilibrada/i })).toBeVisible();
  await expect(page.getByText(/borrador privado/i)).toBeVisible();
  await expect(page.getByRole("heading", { name: "2026-2S" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "2027-1S" })).toBeVisible();
  await page.getByRole("button", { name: /optimizar ruta/i }).click();
  await expect(page.getByText("Ruta encontrada").first()).toBeVisible();
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
