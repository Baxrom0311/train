// Ish vaqti Toshkent bo'yicha (CONTRACT.md §9.2) — talaba boshqa zonada bo'lsa ham.
export const TZ = 'Asia/Tashkent'

const timeFmt = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
const dateTimeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: TZ,
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

export const formatTime = (iso: string | Date) => timeFmt.format(new Date(iso))
export const formatDateTime = (iso: string | Date) => dateTimeFmt.format(new Date(iso))

/** Dedlaynga qolgan vaqt (devor soati): "1:25" yoki "25 daq"; o'tgan bo'lsa null. */
export function remaining(dueIso: string, now: number): { minutes: number; label: string } | null {
  const minutes = Math.floor((new Date(dueIso).getTime() - now) / 60000)
  if (minutes < 0) return null
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return { minutes, label: h ? `${h}:${String(m).padStart(2, '0')}` : `${m}′` }
}

const hourFmt = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: 'numeric', minute: 'numeric', hourCycle: 'h23' })

/** Toshkent bo'yicha soat (o'nli kasr: 13.5 = 13:30). */
export function tashkentHours(at: Date): number {
  const [h, m] = hourFmt.format(at).split(':').map(Number)
  return h + m / 60
}

export type Daypart = 'morning' | 'afternoon' | 'evening'

export function daypart(at: Date): Daypart {
  const h = tashkentHours(at)
  return h < 12 ? 'morning' : h < 16 ? 'afternoon' : 'evening'
}

/** Ish kunining (09:00–18:00) qancha qismi o'tgani, 0..1. */
export function workdayProgress(at: Date): number {
  return Math.min(1, Math.max(0, (tashkentHours(at) - 9) / 9))
}

// Brauzerlarning ko'pida `uz` uchun oy nomlari yo'q ("2026 M09 28") — o'zbekchani o'zimiz yozamiz
const UZ_MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
const dayParts = new Intl.DateTimeFormat('en-US', { timeZone: TZ, day: 'numeric', month: 'numeric', year: 'numeric' })

/** Sana so'z bilan, interfeys tilida: "7-oktabr, 2026" / "7 октября 2026 г." / "7 October 2026". */
export function formatDate(iso: string | Date, lang: string): string {
  const date = new Date(iso)
  if (lang === 'uz') {
    const part = (type: string) => Number(dayParts.formatToParts(date).find((p) => p.type === type)?.value)
    return `${part('day')}-${UZ_MONTHS[part('month') - 1]}, ${part('year')}`
  }
  return new Intl.DateTimeFormat(lang, { timeZone: TZ, day: 'numeric', month: 'long', year: 'numeric' }).format(date)
}
