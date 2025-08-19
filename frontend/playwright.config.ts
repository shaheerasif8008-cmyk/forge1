import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './',
  testMatch: ['tests/e2e/**/*.spec.ts'],
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.FORGE1_FRONTEND_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    video: 'off',
    screenshot: 'only-on-failure',
  },
  timeout: 30_000,
  expect: { timeout: 10_000 },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});


