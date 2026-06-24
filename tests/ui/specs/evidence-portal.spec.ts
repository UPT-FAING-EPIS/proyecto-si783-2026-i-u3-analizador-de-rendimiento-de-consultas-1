import { expect, test } from "@playwright/test";

test("publica los cinco documentos académicos y documentos técnicos", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Query Analyzer/i);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Query Analyzer");
  await expect(page.getByRole("link", { name: /FD01/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /FD05/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Estándar/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Diccionario/ })).toBeVisible();
});

test("permite navegar al manual de usuario", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Manual de Usuario/ }).click();
  await expect(page).toHaveURL(/Manual-de-Usuario\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Manual de Usuario");
});

test("publica el índice completo de reportes", async ({ page }) => {
  await page.goto("/reports/");
  for (const report of ["Cobertura", "Contratos", "Integración", "BDD", "Mutación", "Seguridad"]) {
    await expect(page.getByRole("link", { name: new RegExp(report, "i") })).toBeVisible();
  }
});

test("mantiene legible el portal en viewport móvil", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("main.page")).toBeVisible();
  await expect(page.locator("body")).not.toHaveCSS("overflow-x", "scroll");
});
