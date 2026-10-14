import { defineConfig, devices } from '@playwright/test'

// E2E (CONTRACT.md §34): real backend (Postgres, Redis, arq worker) + soxta LLM,
// barchasi `tools/e2e/stack.sh` ichida soxta soat bilan; frontend — production build.
const API_PORT = process.env.E2E_API_PORT ?? '8100'
const WEB_PORT = process.env.E2E_WEB_PORT ?? '4173'
const CI = Boolean(process.env.CI)

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: CI,
  // §31.2: yiqilgan test sababi topiladi — qayta urinish bilan yashirilmaydi
  retries: 0,
  workers: CI ? 2 : undefined,
  reporter: CI ? [['github'], ['html', { open: 'never' }]] : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    locale: 'uz-UZ',
    timezoneId: 'Asia/Tashkent',
    // PWA keshi (§22) testlar orasida eski bundle bermasin
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: 'bash ../tools/e2e/stack.sh',
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      timeout: 180_000,
      reuseExistingServer: !CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: `npx vite build && npx vite preview --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      timeout: 180_000,
      reuseExistingServer: !CI,
      env: { VITE_API_TARGET: `http://127.0.0.1:${API_PORT}` },
    },
  ],
})
