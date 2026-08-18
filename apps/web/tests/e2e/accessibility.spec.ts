import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

const require = createRequire(import.meta.url);
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

type AxeResult = {
  violations: Array<{
    id: string;
    impact: string | null;
    help: string;
    nodes: Array<{ target: string[] }>;
  }>;
};

const criticalRoutes = [
  "/",
  "/audit",
  "/analytics",
  "/curriculum",
  "/graph?selected=1000003",
  "/planner",
  "/offerings?term=2026-2S",
  "/history",
  "/sources",
  "/login?next=/audit",
] as const;

async function runAxe(page: Page): Promise<AxeResult> {
  await page.addScriptTag({ content: axeSource });
  return page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (root: Document) => Promise<AxeResult> } }).axe;
    return axe.run(document);
  });
}

test.describe("WCAG 2.2 AA critical pages", () => {
  for (const route of criticalRoutes) {
    test(`has no axe violations on ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: "networkidle" });
      await expect(page.locator("#main-content")).toBeVisible();
      const result = await runAxe(page);
      expect(result.violations, result.violations.map((violation) => `${violation.id} [${violation.impact ?? "unknown"}]: ${violation.help} (${violation.nodes.map((node) => node.target.join(" ")).join(", ")})`).join("\n")).toEqual([]);
    });
  }
});

test("core navigation works from the keyboard and restores focus", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toHaveAttribute("href", "#main-content");
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: "networkidle" });
  const menuToggle = page.getByRole("button", { name: /menú/i });
  await menuToggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#mobile-more-menu")).toBeVisible();
  await expect(page.locator("#mobile-more-menu a").first()).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menuToggle).toBeFocused();
  await expect(page.locator("#mobile-more-menu")).toHaveCount(0);
});

test("curriculum and graph selections are keyboard operable and announce the new context", async ({ page }) => {
  await page.goto("/curriculum", { waitUntil: "networkidle" });
  const course = page.getByRole("button", { name: /1000003.*álgebra lineal/i }).first();
  await course.focus();
  await page.keyboard.press("Enter");
  const detailHeading = page.getByRole("heading", { name: "Álgebra lineal", level: 2 });
  await expect(detailHeading).toBeFocused();
  await page.getByRole("button", { name: /cerrar ficha de asignatura/i }).focus();
  await page.keyboard.press("Enter");
  await expect(course).toBeFocused();

  await page.goto("/graph?selected=1000003", { waitUntil: "networkidle" });
  await page.getByText("Alternativa textual accesible", { exact: true }).click();
  await page.getByTestId("graph-textual-course-2000001").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#dependency-focus-title")).toHaveText("2000001");
  await expect(page.locator("#dependency-focus-title")).toBeFocused();
  await expect(page.getByTestId("graph-focus-announcement")).toContainText("2000001");
});

test("planner movement is usable with a keyboard-only alternative on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/planner", { waitUntil: "networkidle" });
  const mobileColumns = await page.locator(".planner-term-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns.trim().split(/\s+/).length);
  expect(mobileColumns).toBe(1);
  const move = page.getByRole("combobox", { name: /mover 1000003 a otro período/i });
  const currentTerm = await move.inputValue();
  const destinationTerm = currentTerm === "00000000-0000-4000-8000-000000000401"
    ? "00000000-0000-4000-8000-000000000402"
    : "00000000-0000-4000-8000-000000000401";
  await move.focus();
  await move.press(currentTerm === "00000000-0000-4000-8000-000000000401" ? "ArrowDown" : "ArrowUp");
  await expect(move).toHaveValue(destinationTerm);
  await expect(page.getByText(/si no puedes arrastrar, usa el selector/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /bloquear 1000003/i })).toBeVisible();
});

test("reduced motion and 200 percent zoom keep the planner usable", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/planner", { waitUntil: "networkidle" });
  const reducedMotion = await page.evaluate(() => {
    const probe = document.createElement("div");
    probe.className = "skeleton";
    document.body.append(probe);
    const style = getComputedStyle(probe);
    const result = { animationDuration: style.animationDuration, scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior };
    probe.remove();
    return result;
  });
  expect(Number.parseFloat(reducedMotion.animationDuration)).toBeLessThan(0.001);
  expect(reducedMotion.scrollBehavior).toBe("auto");

  await page.setViewportSize({ width: 640, height: 900 });
  await page.evaluate(() => { document.documentElement.style.zoom = "2"; });
  const zoomState = await page.evaluate(() => ({
    mainVisible: Boolean(document.querySelector("main")),
    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }));
  expect(zoomState.mainVisible).toBe(true);
  expect(zoomState.horizontalOverflow).toBeLessThanOrEqual(8);
  await expect(page.getByRole("heading", { name: /ruta equilibrada/i })).toBeVisible();
});

test("student journey keeps audit, curriculum, graph and planner connected", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await page.locator('.student-home-facts a[href="/audit"]').click();
  await expect(page.getByRole("heading", { name: /créditos por completar/i })).toBeVisible();
  await page.goto("/curriculum", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /malla curricular/i })).toBeVisible();
  await page.goto("/graph?selected=1000003", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "1000003", level: 1 })).toBeVisible();
  await page.goto("/planner", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /ruta equilibrada/i })).toBeVisible();
});
