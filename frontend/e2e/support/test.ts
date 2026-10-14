// Barcha spec'lar shu `test`dan foydalanadi (CONTRACT.md §34.5): har test oxirida
// backend'da ochiq xato guruhi qolmasligi shart — 5xx, worker xatosi yoki brauzerdagi
// kutilmagan xato (§32) ko'rinadigan tekshiruvlar o'tsa ham testni yiqitadi.
import { expect, test as base } from '@playwright/test'
import { openErrors } from './seed'

// §32.3: xato guruhlari navbatdan bazaga har soniyada yoziladi
const FLUSH_MS = 1_500

export const test = base.extend<{ noServerErrors: void }>({
  noServerErrors: [
    // eslint-disable-next-line no-empty-pattern -- Playwright fixture'i destrukturizatsiya talab qiladi
    async ({}, use) => {
      await use()
      await new Promise((resolve) => setTimeout(resolve, FLUSH_MS))
      expect(openErrors(), "backend/worker/brauzer xatolari (/admin → Xatolar)").toEqual([])
    },
    { auto: true },
  ],
})

export { expect }
