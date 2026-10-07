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
