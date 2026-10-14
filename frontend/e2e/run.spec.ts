// Talaba: ro'yxatdan o'tish → katalog → Run ish stoli (CONTRACT.md §34.4, §9, §14).
import { expect, test } from './support/test'
import { FAKE_FEEDBACK, FAKE_REPLY, FAKE_SCORE } from './support/fakeLlm'
import { PASSWORD, uniqueTag } from './support/seed'

const DAY1 = 'Lazurit Go — Junior Backend dasturchi, 1 kun'

test('yangi talaba katalogdan Run boshlaydi, vazifani topshiradi va baho oladi', async ({ page }) => {
  await test.step("ro'yxatdan o'tish", async () => {
    await page.goto('/register')
    await page.getByLabel("To'liq ism").fill('Madina Yusupova')
    await page.getByLabel('Elektron pochta').fill(`yangi-${uniqueTag()}@e2e.tryjob.uz`)
    await page.getByLabel('Parol', { exact: true }).fill(PASSWORD)
    await page.getByLabel('Parolni tasdiqlash').fill(PASSWORD)
    await page.getByRole('button', { name: "Ro'yxatdan o'tish" }).last().click()
    await expect(page).toHaveURL(/\/simulations$/)
    await expect(page.getByRole('heading', { name: 'Simulyatsiyalar', level: 1 })).toBeVisible()
  })

  await test.step('katalog: soha, format va qidiruv filtrlari', async () => {
    const cards = page.getByRole('heading', { level: 3 })
    await expect(cards.first()).toBeVisible()
    const total = await cards.count()
    expect(total).toBeGreaterThanOrEqual(15)   // backend/content/scenarios — 5 soha × 3 format

    await page.getByRole('group', { name: 'Soha' }).getByRole('button', { name: 'IT' }).click()
    await page.getByRole('group', { name: 'Format' }).getByRole('button', { name: '1 kunlik' }).click()
    await expect(cards).toHaveText([DAY1])

    await page.getByRole('group', { name: 'Soha' }).getByRole('button', { name: 'Hammasi' }).click()
    await page.getByRole('textbox', { name: 'Qidirish...' }).fill('sabzazor')
    await expect(cards).toHaveText([/^Sabzazor — Junior Data analyst, 1 kun$/])
    await page.getByRole('textbox', { name: 'Qidirish...' }).fill('')
    await page.getByRole('group', { name: 'Format' }).getByRole('button', { name: 'Barcha formatlar' }).click()
    await expect(cards).toHaveCount(total)
  })

  await test.step('Run boshlash', async () => {
    await page.getByRole('button', { name: `Boshlash: ${DAY1}` }).click()
    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]{36}$/)
    await expect(page.getByRole('heading', { name: DAY1, level: 1 })).toBeVisible()
    await expect(page.getByText('Faol', { exact: true })).toBeVisible()
  })

  const inbox = page.getByRole('complementary').filter({ hasText: 'Kiruvchi' })
  const task = page.getByRole('main').getByRole('article')
  const chat = page.getByRole('complementary').filter({ has: page.getByRole('textbox', { name: /Xabar yozing/ }) })

  await test.step("09:00 dagi xabar va standup vazifasi keladi", async () => {
    await expect(inbox.getByRole('button', { name: /Xush kelibsiz, Lazurit Go/ })).toBeVisible()
    await inbox.getByRole('button', { name: /Standup vaqti/ }).click()
    await expect(task.getByText('Javob kutilmoqda')).toBeVisible()
    await expect(task.getByText(/Dedlayn:/)).toBeVisible()
  })

  await test.step('ilova qilingan hujjat ochiladi', async () => {
    await task.getByRole('button', { name: 'Backend jamoasi: onboarding' }).click()
    const doc = page.getByRole('dialog')
    await expect(doc.getByRole('heading', { name: 'Backend jamoasi: onboarding' })).toBeVisible()
    await expect(doc).toContainText('Standup formati')
    await doc.getByRole('button', { name: 'Yopish' }).click()
    await expect(doc).toBeHidden()
  })

  await test.step('javob topshiriladi va AI bahosi jonli keladi', async () => {
    const send = task.getByRole('button', { name: 'Yuborish' })
    await expect(send).toBeDisabled()
    await task.getByRole('textbox', { name: 'Matn' }).fill(
      "Bugun: onboarding va orders-service kodi bilan tanishaman.\n"
      + "Natija: birinchi ticket bo'yicha sababni topib, PR ochaman.\n"
      + "To'siq: staging'ga kirish huquqi yo'q — Sardordan so'rayman.",
    )
    await send.click()
    await expect(task.getByText('Topshirildi')).toBeVisible()
    // baholash arq worker'ida (soxta LLM), natija SSE orqali sahifani yangilaydi
    await expect(task.getByText(FAKE_FEEDBACK)).toBeVisible({ timeout: 30_000 })
    await expect(task.getByText(FAKE_SCORE, { exact: true })).toBeVisible()
    await expect(task.getByText('Urinish 1/3')).toBeVisible()
    await expect(task.getByRole('button', { name: 'Qayta yuborish (2)' })).toBeEnabled()
  })

  await test.step('mentor baholangan urinishga chatda izoh yozadi (§9.13)', async () => {
    const mentor = chat.getByRole('button', { name: /^NR Nodir/ })
    await expect(mentor).toHaveAccessibleName(/^NR Nodir 1$/, { timeout: 30_000 })
    await mentor.click()
    await expect(chat.getByText("Task bo'yicha izoh")).toBeVisible()
    await expect(chat).toContainText(FAKE_FEEDBACK)
  })

  await test.step('personaj bilan chat', async () => {
    await chat.getByRole('button', { name: /^SQ Sardor/ }).click()
    const box = chat.getByRole('textbox', { name: /Xabar yozing/ })
    await box.fill("Salom, staging'ga kirish huquqini kimdan so'rayman?")
    await box.press('Enter')
    await expect(chat.getByText("Salom, staging'ga kirish huquqini kimdan so'rayman?")).toBeVisible()
    await expect(chat.getByText(FAKE_REPLY)).toBeVisible({ timeout: 30_000 })
  })

  await test.step('sahifa qayta yuklanganda holat saqlanadi', async () => {
    await page.reload()
    await inbox.getByRole('button', { name: /Standup vaqti/ }).click()
    await expect(task.getByText(FAKE_FEEDBACK)).toBeVisible()
    await page.getByRole('link', { name: 'Simulyatsiyalar' }).first().click()
    await expect(page.getByText('Davom etayotgan simulyatsiya')).toBeVisible()
    await expect(page.getByRole('button', { name: `Boshlash: ${DAY1}` })).toBeDisabled()
  })
})
