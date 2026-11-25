import { createHmac } from 'node:crypto';
import { expect, test } from '@playwright/test';

function createTotp(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of secret) {
    bits += alphabet.indexOf(character).toString(2).padStart(5, '0');
  }

  const key = Buffer.from(bits.match(/.{8}/g)?.map((byte) => parseInt(byte, 2)) || []);
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const value = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(value % 1_000_000).padStart(6, '0');
}

test('registration and session endpoints are reachable through the frontend origin', async ({ request }) => {
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const email = `proxy-${suffix}@example.com`;
  const password = 'Reliable-Proxy-Test-2026!';

  const healthResponse = await request.get('/api/health');
  expect(healthResponse.status()).toBe(200);
  expect(await healthResponse.json()).toMatchObject({ status: 'ok' });

  const registerResponse = await request.post('/api/auth/register', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    data: { email, password },
  });
  expect(registerResponse.status()).toBe(200);

  const weakPasswordResponse = await request.post('/api/auth/register', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    data: { email: `weak-${suffix}@example.com`, password: '123456789' },
  });
  expect(weakPasswordResponse.status()).toBe(400);
  expect((await weakPasswordResponse.json()).error.message).toContain('too common');

  const loginResponse = await request.post('/api/auth/login', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    data: { email, password },
  });
  expect(loginResponse.status()).toBe(200);
  expect(loginResponse.headers()['set-cookie']).toMatch(/HttpOnly/i);
});

test('browser can register, log in, enrol MFA, and verify an MFA sign-in', async ({ page }) => {
  test.setTimeout(90_000);
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const email = `ui-${suffix}@example.com`;
  const password = 'Reliable-UI-Test-2026!';
  let secret = '';

  await page.goto('/register');
  await page.locator('#register-email').fill(email);
  await page.locator('#register-password').fill(password);
  await page.locator('#register-confirm-password').fill(password);
  await page.getByRole('button', { name: 'Create Account' }).click();
  await expect(page.locator('div[role="status"].bg-green-50')).toContainText('Account created successfully');
  await page.getByRole('link', { name: 'Sign In Now' }).click();

  await page.locator('#login-email').fill(email);
  await page.locator('#login-password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('heading', { name: 'Set Up Multi-Factor Authentication' })).toBeVisible();

  secret = await page.locator('#totp-secret-key').innerText();
  await page.locator('#totp-confirm-input').fill(createTotp(secret));
  await page.getByRole('button', { name: 'Confirm and Enable MFA' }).click();
  await expect(page.getByRole('heading', { name: 'Save Your Recovery Codes' })).toBeVisible();
  await page.locator('#saved-codes-checkbox').check();
  await page.getByRole('button', { name: 'Continue to Dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Account Dashboard' })).toBeVisible();
  await page.getByRole('button', { name: 'Sign Out', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Sign In to Nexis' })).toBeVisible();

  const secondsIntoStep = (Date.now() / 1000) % 30;
  await page.waitForTimeout((30 - secondsIntoStep) * 1000 + 250);
  await page.locator('#login-email').fill(email);
  await page.locator('#login-password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page.getByRole('heading', { name: 'Two-Step Verification' })).toBeVisible();

  const loginCookie = await page.context().cookies();
  expect(loginCookie.some((cookie) => cookie.name === 'nexis_session' && cookie.httpOnly)).toBe(true);
  await page.locator('#totp-verify-input').fill(createTotp(secret));
  await page.getByRole('button', { name: 'Verify Code & Sign In' }).click();
  await expect(page.getByRole('heading', { name: 'Account Dashboard' })).toBeVisible();
});
