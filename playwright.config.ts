import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e', timeout: 60000, workers: 1,
  use: { baseURL: process.env.E2E_BASE_URL || 'http://localhost:8443', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure' },
  reporter: [['list']],
})
