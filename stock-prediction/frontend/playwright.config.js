/**
 * playwright.config.js — Playwright E2E test configuration
 * ==========================================================
 * Runs end-to-end tests against the locally-served Vite dev server.
 *
 * Usage:
 *   npx playwright install --with-deps chromium
 *   npx playwright test
 *   npx playwright test --ui           # interactive mode
 *   npx playwright show-report         # view HTML report
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: [
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["list"],
  ],

  use: {
    baseURL:     process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173",
    trace:       "on-first-retry",
    screenshot:  "only-on-failure",
    video:       "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "Mobile Safari",
      use: { ...devices["iPhone 12"] },
    },
  ],

  // Start the Vite dev server automatically before running tests
  webServer: {
    command: "npm run dev",
    url:     "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
