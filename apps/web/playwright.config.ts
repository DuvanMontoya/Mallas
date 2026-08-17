import { defineConfig, devices } from "@playwright/test";

process.env.API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8010";
process.env.PORT = process.env.PLAYWRIGHT_PORT ?? "3100";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "node tests/e2e/fixture-server.mjs",
      url: "http://127.0.0.1:8010/health",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "pnpm start",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
