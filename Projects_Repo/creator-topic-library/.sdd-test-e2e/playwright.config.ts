import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 90_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5199',
    channel: 'chrome',
    screenshot: 'only-on-failure',
    trace: 'off',
    viewport: { width: 1440, height: 1000 },
  },
  reporter: [['line']],
})
