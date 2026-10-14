// Kompaniya vakansiya e'lon qiladi → talaba ariza beradi → kompaniya taklif yuboradi →
// talaba qabul qiladi (CONTRACT.md §34.4, §23, §10, §15). Ikki foydalanuvchi — ikki brauzer konteksti.
import { expect, test } from './support/test'
import { login } from './support/auth'
import { seedCompany, seedStudent, uniqueTag } from './support/seed'

test('vakansiyaga ariza va ish taklifi: kompaniya ↔ talaba', async ({ browser }) => {
  const tag = uniqueTag()
  const title = `Junior Backend dasturchi ${tag}`
  const hr = seedCompany('Dilnoza Karimova', `Yulduzcha Soft ${tag}`)
  // profil real yo'l bilan: tugallangan Run, yakuniy hisobot (Muloqot = 80)
  const student = seedStudent('Aziz Rahimov', { completed: 'lazurit-go-backend-day1' })

  const company = await (await browser.newContext()).newPage()
  const candidate = await (await browser.newContext()).newPage()
  await login(company, hr)
  await login(candidate, student)

  await test.step("kompaniya talablar bilan vakansiya e'lon qiladi", async () => {
    await company.getByRole('link', { name: 'Vakansiyalar' }).first().click()
    await company.getByRole('link', { name: 'Yangi vakansiya' }).click()
    await company.getByLabel('Lavozim').fill(title)
    await company.getByLabel('Tavsif').fill("Go va PostgreSQL bilan buyurtmalar xizmatida ishlaydigan junior dasturchi.")
    await company.getByLabel('Soha').selectOption('IT')
    await company.getByRole('checkbox', { name: 'Muloqot' }).check()
    await company.getByRole('slider', { name: 'Muloqot' }).fill('50')
    await company.getByRole('checkbox', { name: /^Lazurit Go — Junior Backend dasturchi, 1 kun/ }).check()
    await company.getByRole('button', { name: "E'lon qilish" }).click()

    await expect(company).toHaveURL(/\/company\/vacancies\/[0-9a-f-]{36}$/)
    await expect(company.getByRole('heading', { name: title, level: 1 })).toBeVisible()
    await expect(company.getByText('Ochiq', { exact: true })).toBeVisible()
    await expect(company.getByRole('listitem').filter({ hasText: /^Muloqot\s*≥ 50$/ })).toBeVisible()
    await expect(company.getByRole('radio', { name: 'Arizalar (0)' })).toBeChecked()
  })

  await test.step('talaba moslikni ko\'radi va ariza beradi', async () => {
    await candidate.getByRole('link', { name: 'Vakansiyalar' }).first().click()
    const card = candidate.getByRole('link', { name: new RegExp(title) })
    await expect(card).toContainText('100% mos')
    await expect(card).toContainText(hr.company)
    await card.click()

    await expect(candidate.getByRole('heading', { name: title, level: 1 })).toBeVisible()
    await expect(candidate.getByRole('listitem').filter({ hasText: /^Muloqot\s*80 \/ 50$/ })).toBeVisible()
    await expect(candidate.getByRole('heading', { name: 'Mashq qiling' })).toBeVisible()

    const panel = candidate.getByRole('complementary')
    await panel.getByRole('textbox', { name: 'Izoh' }).fill("Buyurtmalar xizmatidagi bug'ni simulyatsiyada tuzatganman.")
    await panel.getByRole('button', { name: 'Ariza berish' }).click()
    await expect(panel.getByText('Ariza berilgan')).toBeVisible()
    await expect(panel.getByRole('button', { name: 'Arizani qaytarib olish' })).toBeVisible()
  })

  await test.step('kompaniya arizani ko\'radi va taklif yuboradi', async () => {
    await company.reload()
    await expect(company.getByRole('radio', { name: 'Arizalar (1)' })).toBeChecked()
    await expect(company.getByText(student.name, { exact: true })).toBeVisible()
    await expect(company.getByText("“Buyurtmalar xizmatidagi bug'ni simulyatsiyada tuzatganman.”")).toBeVisible()
    // email taklif qabul qilinmaguncha ko'rinmaydi (§10.4)
    await expect(company.getByText(student.email)).toHaveCount(0)

    await company.getByRole('button', { name: 'Taklif yuborish' }).click()
    const dialog = company.getByRole('dialog')
    await expect(dialog.getByLabel('Lavozim')).toHaveValue(title)
    await dialog.getByLabel('Xabar').fill("Simulyatsiyadagi natijangiz yoqdi. Ertaga 11:00 da ofisga suhbatga taklif qilamiz.")
    await dialog.getByRole('button', { name: 'Yuborish' }).click()
    await expect(dialog.getByText(/^Taklif yuborildi\./)).toBeVisible()
    await dialog.getByRole('button', { name: 'Yopish' }).click()
    await expect(company.getByText('Taklif yuborilgan')).toBeVisible()
  })

  await test.step('talaba bildirishnoma oladi va taklifni qabul qiladi', async () => {
    await candidate.goto('/offers')
    await expect(candidate.getByText(title, { exact: true })).toBeVisible()
    await expect(candidate.getByText('Ertaga 11:00 da ofisga suhbatga taklif qilamiz.', { exact: false })).toBeVisible()
    await expect(candidate.getByRole('button', { name: /^Bildirishnomalar: \d+ ta yangi$/ })).toBeVisible()

    await candidate.getByRole('button', { name: 'Qabul qilish' }).click()
    await expect(candidate.getByText(`${hr.company} emailingizni ko'radi va siz bilan bog'lanadi.`)).toBeVisible()
    await candidate.getByRole('button', { name: 'Tasdiqlash' }).click()
    await expect(candidate.getByText("Kompaniya emailingizni oldi va tez orada bog'lanadi.")).toBeVisible()
  })

  await test.step('kompaniya javobni va nomzod emailini ko\'radi', async () => {
    await company.getByRole('link', { name: 'Takliflarim' }).click()
    await expect(company.getByText(title)).toBeVisible()
    await expect(company.getByText('Qabul qilindi').first()).toBeVisible()
    await expect(company.getByText(student.email)).toBeVisible()
  })
})
