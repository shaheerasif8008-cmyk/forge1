import { test, expect } from '@playwright/test';

const FE = process.env.FORGE1_FRONTEND_URL || 'http://localhost:3000';
const EMAIL = process.env.FORGE1_E2E_EMAIL || 'demo@example.com';
const PASSWORD = process.env.FORGE1_E2E_PASSWORD || 'admin';

test('login -> dashboard metrics visible', async ({ page }) => {
  await page.goto(`${FE}/login`);
  await page.getByLabel('Email').fill(EMAIL);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/.*dashboard/);
  await expect(page.getByText(/Your AI workforce at a glance/)).toBeVisible();
  await expect(page.getByText(/Requests/)).toBeVisible();
});

test('create employee from template -> success toast', async ({ page }) => {
  await page.goto(`${FE}/login`);
  await page.getByLabel('Email').fill(EMAIL);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.goto(`${FE}/builder`);
  // Assume a template grid; pick first template card button
  await page.getByRole('button', { name: /create/i }).first().click();
  await expect(page.getByText(/created/i)).toBeVisible({ timeout: 10000 });
});

test('run task -> logs show entry', async ({ page }) => {
  await page.goto(`${FE}/login`);
  await page.getByLabel('Email').fill(EMAIL);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.goto(`${FE}/employees`);
  // Open first employee
  await page.getByRole('link').filter({ hasText: /employee|agent/i }).first().click();
  await page.getByRole('textbox').fill('Hello from E2E');
  await page.getByRole('button', { name: /run/i }).click();
  // Navigate to logs via trace link
  await page.getByRole('link', { name: /trace|logs/i }).first().click();
  await expect(page.getByText(/Hello from E2E/)).toBeVisible({ timeout: 15000 });
});

test('metrics page renders charts', async ({ page }) => {
  await page.goto(`${FE}/login`);
  await page.getByLabel('Email').fill(EMAIL);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.goto(`${FE}/metrics`);
  await expect(page.getByText(/Traffic/)).toBeVisible();
});


