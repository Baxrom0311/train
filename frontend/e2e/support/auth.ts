import { expect, type Page } from '@playwright/test'
import type { Account } from './seed'

/** Login sahifasi orqali kirish; bosh sahifaga o'tishini kutadi. */
export async function login(page: Page, account: Pick<Account, 'email' | 'password'>) {
  await page.goto('/login')
  await page.getByLabel('Elektron pochta').fill(account.email)
  await page.getByLabel('Parol', { exact: true }).fill(account.password)
  await page.getByLabel('Parol', { exact: true }).press('Enter')
  await expect(page).not.toHaveURL(/\/login/)
}
