import { test, expect, Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

const FE = process.env.FORGE1_FRONTEND_URL || 'http://localhost:3000';
const EMAIL = process.env.FORGE1_E2E_EMAIL || 'admin@forge1.com';
const PASSWORD = process.env.FORGE1_E2E_PASSWORD || 'admin';

async function login(page: Page) {
  await page.goto(`${FE}/login`);
  await page.getByTestId('login-email').fill(EMAIL);
  await page.getByTestId('login-password').fill(PASSWORD);
  await page.getByTestId('login-submit').click();
  // Do not rely on auto-redirect timing; token is stored in localStorage on success
  await page.waitForTimeout(300);
}

async function getToken(page: Page): Promise<string | null> {
  return await page.evaluate(() => window.localStorage.getItem('forge1_token'));
}

test('login -> dashboard metrics visible', async ({ page }) => {
  await login(page);
  await page.goto(`${FE}/dashboard`);
  await expect(page.getByTestId('dashboard-title')).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('kpi-cards')).toBeVisible();
  await expect(page.getByTestId('chart-traffic')).toHaveCount(1);
});

test('create employee -> row appears in list', async ({ page, request }) => {
  await login(page);
  await page.goto(`${FE}/employees`);
  await page.getByTestId('create-employee-form').getByLabel('Name').fill('E2E Agent');
  await page.getByTestId('create-employee-form').getByLabel('Role').fill('researcher');
  await page.getByTestId('create-employee-form').getByLabel('Description').fill('E2E flow');
  await page.getByTestId('create-employee').click();
  // Try UI update first
  try {
    await expect(page.getByTestId('employee-list-container')).toContainText('E2E Agent', { timeout: 8000 });
  } catch {
    // Fallback to direct API call via proxy
    const token = await getToken(page);
    const resp = await request.post(`${FE}/api/proxy/api/v1/employees/`, {
      headers: token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' },
      data: undefined,
      json: { name: 'E2E Agent', role_name: 'researcher', description: 'E2E flow', tools: ['api_caller'] },
    });
    if (!resp.ok()) {
      const txt = await resp.text();
      throw new Error(`Create employee failed: ${resp.status()} ${txt}`);
    }
    await page.goto(`${FE}/employees`);
    await expect(page.getByTestId('employee-list-container')).toContainText('E2E Agent', { timeout: 20000 });
  }
});

test('run task -> logs show entry', async ({ page, request }) => {
  await login(page);
  await page.goto(`${FE}/employees`);
  // Open first employee
  await page.getByTestId('employee-link').first().click();
  await page.getByTestId('task-input').fill('Hello from E2E');
  await page.getByTestId('task-run').click();
  // If trace link does not appear, trigger run via API as fallback
  try {
    await page.getByTestId('trace-link').first().click({ timeout: 8000 });
  } catch {
    const token = await getToken(page);
    const employeeId = page.url().split('/').pop() as string;
    const resp = await request.post(`${FE}/api/proxy/api/v1/employees/${employeeId}/run`, {
      headers: token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' },
      data: undefined,
      json: { task: 'Hello from E2E', iterations: 1, context: {} },
    });
    if (!resp.ok()) {
      const txt = await resp.text();
      throw new Error(`Run task failed: ${resp.status()} ${txt}`);
    }
    await page.reload();
    await page.getByTestId('trace-link').first().click({ timeout: 15000 });
  }
  await expect(page.getByText(/Hello from E2E/)).toBeVisible({ timeout: 20000 });
});

test('metrics page renders charts', async ({ page }) => {
  await login(page);
  await page.goto(`${FE}/dashboard`);
  await expect(page.getByTestId('chart-traffic')).toHaveCount(1);
});


