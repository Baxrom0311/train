// Tugallangan Run: hisobot → sertifikat → ochiq tekshiruv sahifasi (CONTRACT.md §34.4, §9.6, §13).
import { expect, test } from './support/test'
import { login } from './support/auth'
import { seedStudent } from './support/seed'

const DAY1 = 'Lazurit Go — Junior Backend dasturchi, 1 kun'

test('talaba hisobotni ko\'radi, sertifikatni mehmon ham tekshira oladi', async ({ page, browser }) => {
  // seed: 6 ta node, ballar 80/90/100(qaror)/70/75/80 — umumiy ball 82
  const student = seedStudent('Aziz Rahimov', { completed: 'lazurit-go-backend-day1' })
  await login(page, student)

  let certUrl = ''
  await test.step('katalog tarixidan hisobotga', async () => {
    await page.goto('/simulations')
    await expect(page.getByRole('heading', { name: 'Oldingi simulyatsiyalar' })).toBeVisible()
    await page.getByRole('link', { name: 'Hisobot' }).click()
    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]{36}\/report$/)
    await expect(page.getByText('Yakunlangan', { exact: true })).toBeVisible()
    await expect(page.getByText('82', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('6/6', { exact: true })).toBeVisible()
    await expect(page.getByRole('row')).toHaveCount(7)   // sarlavha + 6 node

    const code = page.getByText(/^TJ-[A-Z0-9]{4}-[A-Z0-9]{4}$/)
    await expect(code).toBeVisible()
    certUrl = (await page.getByRole('link', { name: 'Sertifikatni ochish' }).getAttribute('href')) ?? ''
    expect(certUrl).toBe(`/c/${await code.textContent()}`)
  })

  await test.step('mehmon sertifikatni ochiq havola bilan tekshiradi', async () => {
    const guest = await (await browser.newContext()).newPage()
    await guest.goto(certUrl)
    await expect(guest.getByText('Sertifikat haqiqiy — TryJob tomonidan berilgan')).toBeVisible()
    // uz-UZ brauzerida ham o'zbekcha oy nomi ("2026 M10 16" emas)
    await expect(guest.getByText(/^Berilgan sana: \d{1,2}-[a-z']+, \d{4}$/)).toBeVisible()
    const sheet = guest.getByRole('article')
    await expect(sheet.getByRole('heading', { name: student.name, level: 1 })).toBeVisible()
    await expect(sheet).toContainText(`«${DAY1}»`)
    await expect(sheet.getByText('82', { exact: true })).toBeVisible()
    await expect(sheet.getByRole('img', { name: 'Sertifikat sahifasiga QR havola' })).toBeVisible()
  })
})
