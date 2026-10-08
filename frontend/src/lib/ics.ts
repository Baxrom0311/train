// Kalendar fayli (.ics, RFC 5545) — suhbatni telefon/kompyuter kalendariga qo'shish (CONTRACT.md §25.6).
// Brauzerda yaratiladi: server hech narsa saqlamaydi.

const stamp = (d: Date) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')

/** Matn maydonlari: `\`, `;`, `,` va yangi qator qochiriladi. */
const escape = (s: string) => s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n')

const encoder = new TextEncoder()

/** 75 baytdan uzun qator bo'linadi; ko'p baytli (kirill, emoji) belgi o'rtasidan kesilmaydi. */
function fold(line: string): string {
  const out: string[] = []
  let current = ''
  let bytes = 0
  for (const ch of line) {
    const size = encoder.encode(ch).length
    // davom qatori bo'sh joy bilan boshlanadi — u ham 75 baytga kiradi
    if (bytes + size > (out.length ? 74 : 75)) {
      out.push(current)
      current = ''
      bytes = 0
    }
    current += ch
    bytes += size
  }
  out.push(current)
  return out.join('\r\n ')
}

export interface CalendarEvent {
  uid: string
  start: Date
  minutes: number
  title: string
  description?: string
  location?: string
  url?: string
}

export function buildIcs(e: CalendarEvent, now = new Date()): string {
  const end = new Date(e.start.getTime() + e.minutes * 60_000)
  const lines = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//TryJob//Interview//UZ', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${e.uid}@tryjob`,
    `DTSTAMP:${stamp(now)}`,
    `DTSTART:${stamp(e.start)}`,
    `DTEND:${stamp(end)}`,
    `SUMMARY:${escape(e.title)}`,
    ...(e.description ? [`DESCRIPTION:${escape(e.description)}`] : []),
    ...(e.location ? [`LOCATION:${escape(e.location)}`] : []),
    ...(e.url ? [`URL:${e.url}`] : []),
    'BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${escape(e.title)}`, 'TRIGGER:-PT30M', 'END:VALARM',
    'END:VEVENT', 'END:VCALENDAR',
  ]
  return lines.map(fold).join('\r\n') + '\r\n'
}

export function downloadIcs(e: CalendarEvent, filename = 'interview.ics') {
  const url = URL.createObjectURL(new Blob([buildIcs(e)], { type: 'text/calendar;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
